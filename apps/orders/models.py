from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid
import datetime

from apps.users.models import Utilisateur
from apps.catalog.models import Produit, VarianteProduit, OptionProduit, Etablissement


class Panier(models.Model):
    """
    Panier d'achat actif d'un Client AYYOU.
    Un Client ne possède qu'un seul panier actif à la fois.
    Le panier peut contenir des produits provenant de plusieurs établissements.
    """
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='paniers',
        verbose_name=_('utilisateur')
    )
    actif = models.BooleanField(_('est actif'), default=True)
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Panier')
        verbose_name_plural = _('Paniers')
        ordering = ['-date_modification']
        constraints = [
            models.UniqueConstraint(
                fields=['utilisateur'],
                condition=models.Q(actif=True),
                name='unique_panier_actif_utilisateur'
            )
        ]

    def __str__(self):
        statut_str = "Actif" if self.actif else "Inactif"
        return f"Panier #{self.id} de {self.utilisateur.get_full_name()} ({statut_str})"

    def calculer_total(self) -> Decimal:
        """
        Calcule le montant total de tous les articles du panier.
        """
        total = Decimal('0.00')
        for item in self.items.all():
            total += item.calculer_total_ligne()
        return total


class PanierItem(models.Model):
    """
    Article présent dans un Panier Client.
    Conserve le produit, la quantité, la variante choisie et les options/sauces/suppléments.
    """
    id = models.BigAutoField(primary_key=True)
    panier = models.ForeignKey(
        Panier,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('panier')
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='panier_items',
        verbose_name=_('produit')
    )
    quantite = models.PositiveIntegerField(_('quantité'), default=1)
    prix_unitaire = models.DecimalField(_('prix unitaire snapshot (FCFA)'), max_digits=10, decimal_places=2)
    variante = models.ForeignKey(
        VarianteProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='panier_items',
        verbose_name=_('variante choisie')
    )
    options = models.ManyToManyField(
        OptionProduit,
        blank=True,
        related_name='panier_items',
        verbose_name=_('options / suppléments choisis')
    )
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Article de Panier')
        verbose_name_plural = _('Articles de Panier')
        ordering = ['-date_creation']

    def clean(self):
        super().clean()
        if self.quantite < 1:
            raise ValidationError(_("La quantité d'un article de panier doit être d'au moins 1."))

    def save(self, *args, **kwargs):
        self.clean()
        if not self.prix_unitaire and self.produit:
            self.prix_unitaire = self.produit.prix_base
        super().save(*args, **kwargs)

    def calculer_prix_total_unitaire(self) -> Decimal:
        """
        Calcule le prix unitaire complet d'une portion (prix base + variante + options).
        """
        prix = Decimal(str(self.prix_unitaire))
        if self.variante:
            prix += Decimal(str(self.variante.surcout_prix))
        if self.pk:
            for opt in self.options.all():
                prix += Decimal(str(opt.surcout_prix))
        return prix

    def calculer_total_ligne(self) -> Decimal:
        """
        Calcule le total de la ligne (prix unitaire complet * quantité).
        """
        return self.calculer_prix_total_unitaire() * Decimal(str(self.quantite))

    def __str__(self):
        return f"{self.quantite}x {self.produit.nom} dans Panier #{self.panier_id}"


class Commande(models.Model):
    """
    Commande globale passée par un Client AYYOU.
    Regroupe une ou plusieurs SousCommandes par établissement (multi-établissements).
    Conserve les snapshots de l'adresse de livraison et du destinataire.
    """
    STATUT_BROUILLON = 'BROUILLON'
    STATUT_EN_ATTENTE_PAIEMENT = 'EN_ATTENTE_PAIEMENT'
    STATUT_PAYEE = 'PAYEE'
    STATUT_EN_PREPARATION = 'EN_PREPARATION'
    STATUT_PRETE = 'PRETE'
    STATUT_EN_LIVRAISON = 'EN_LIVRAISON'
    STATUT_LIVREE = 'LIVREE'
    STATUT_ANNULEE = 'ANNULEE'

    CHOIX_STATUTS = [
        (STATUT_BROUILLON, _('Brouillon')),
        (STATUT_EN_ATTENTE_PAIEMENT, _('En attente de paiement')),
        (STATUT_PAYEE, _('Payée')),
        (STATUT_EN_PREPARATION, _('En préparation')),
        (STATUT_PRETE, _('Prête')),
        (STATUT_EN_LIVRAISON, _('En livraison')),
        (STATUT_LIVREE, _('Livrée')),
        (STATUT_ANNULEE, _('Annulée')),
    ]

    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='commandes',
        verbose_name=_('client')
    )
    numero_commande = models.CharField(
        _('numéro de commande'),
        max_length=50,
        unique=True,
        db_index=True
    )
    statut = models.CharField(
        _('statut de la commande'),
        max_length=30,
        choices=CHOIX_STATUTS,
        default=STATUT_EN_ATTENTE_PAIEMENT,
        db_index=True
    )

    sous_total = models.DecimalField(_('sous-total (FCFA)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    frais_livraison = models.DecimalField(_('frais de livraison (FCFA)'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(_('total général (FCFA)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))

    # Snapshot Adresse de livraison
    adresse_livraison = models.CharField(_('adresse de livraison'), max_length=255)
    latitude_livraison = models.DecimalField(_('latitude livraison'), max_digits=10, decimal_places=7, null=True, blank=True)
    longitude_livraison = models.DecimalField(_('longitude livraison'), max_digits=10, decimal_places=7, null=True, blank=True)
    instructions_livraison = models.TextField(_('instructions de livraison'), blank=True, default='')

    # Snapshot Destinataire
    nom_destinataire = models.CharField(_('nom du destinataire'), max_length=150)
    telephone_destinataire = models.CharField(_('téléphone du destinataire'), max_length=30)

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True, db_index=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Commande')
        verbose_name_plural = _('Commandes')
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['utilisateur', 'statut']),
            models.Index(fields=['numero_commande']),
        ]

    def clean(self):
        super().clean()
        if self.sous_total < 0 or self.frais_livraison < 0 or self.total < 0:
            raise ValidationError(_("Les montants de la commande ne peuvent pas être négatifs."))

    def save(self, *args, **kwargs):
        if not self.numero_commande:
            self.numero_commande = self.generer_numero_commande()
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def generer_numero_commande(cls) -> str:
        """
        Génère un numéro de commande unique lisible pour le Client (ex: AYY-20260916-A1B2C3).
        """
        date_str = datetime.date.today().strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        return f"AYY-{date_str}-{suffix}"

    def recalculer_totaux(self):
        """
        Recalcule le sous-total et le total à partir des sous-commandes associées.
        """
        st = Decimal('0.00')
        fl = Decimal('0.00')
        for sc in self.sous_commandes.all():
            st += sc.sous_total
            fl += sc.frais_livraison
        self.sous_total = st
        self.frais_livraison = fl
        self.total = st + fl
        self.save(update_fields=['sous_total', 'frais_livraison', 'total', 'date_modification'])

    def __str__(self):
        return f"Commande {self.numero_commande} ({self.get_statut_display()}) - {self.total} FCFA"


class SousCommande(models.Model):
    """
    Sous-commande rattachée à un Établissement spécifique.
    Permet le découpage automatique d'une Commande multi-établissements.
    """
    id = models.BigAutoField(primary_key=True)
    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name='sous_commandes',
        verbose_name=_('commande principale')
    )
    etablissement = models.ForeignKey(
        Etablissement,
        on_delete=models.CASCADE,
        related_name='sous_commandes',
        verbose_name=_('établissement')
    )
    statut = models.CharField(
        _('statut de la sous-commande'),
        max_length=30,
        choices=Commande.CHOIX_STATUTS,
        default=Commande.STATUT_EN_ATTENTE_PAIEMENT,
        db_index=True
    )
    sous_total = models.DecimalField(_('sous-total établissement (FCFA)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    frais_livraison = models.DecimalField(_('frais livraison établissement (FCFA)'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(_('total établissement (FCFA)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Sous-Commande Établissement')
        verbose_name_plural = _('Sous-Commandes Établissements')
        ordering = ['id']

    def clean(self):
        super().clean()
        if self.sous_total < 0 or self.frais_livraison < 0 or self.total < 0:
            raise ValidationError(_("Les montants de la sous-commande ne peuvent pas être négatifs."))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def recalculer_totaux(self):
        """
        Recalcule le sous-total de la sous-commande d'après ses LigneCommande.
        """
        st = Decimal('0.00')
        for ligne in self.lignes.all():
            st += ligne.total_ligne
        self.sous_total = st
        self.total = st + self.frais_livraison
        self.save(update_fields=['sous_total', 'total', 'date_modification'])

    def __str__(self):
        return f"Sous-Commande #{self.id} ({self.etablissement.nom}) pour {self.commande.numero_commande}"


class LigneCommande(models.Model):
    """
    Ligne individuelle d'une SousCommande représentant un produit acheté.
    Conserve un snapshot du nom du produit et du prix au moment de l'achat.
    """
    id = models.BigAutoField(primary_key=True)
    sous_commande = models.ForeignKey(
        SousCommande,
        on_delete=models.CASCADE,
        related_name='lignes',
        verbose_name=_('sous-commande')
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lignes_commande',
        verbose_name=_('produit catalogue')
    )
    nom_produit_snapshot = models.CharField(_('nom du produit (snapshot)'), max_length=200)
    quantite = models.PositiveIntegerField(_('quantité'), default=1)
    prix_unitaire = models.DecimalField(_('prix unitaire (FCFA)'), max_digits=10, decimal_places=2)
    total_ligne = models.DecimalField(_('total ligne (FCFA)'), max_digits=12, decimal_places=2)
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Ligne de Commande')
        verbose_name_plural = _('Lignes de Commande')
        ordering = ['id']

    def clean(self):
        super().clean()
        if self.quantite < 1:
            raise ValidationError(_("La quantité d'une ligne de commande doit être d'au moins 1."))
        if self.prix_unitaire < 0 or self.total_ligne < 0:
            raise ValidationError(_("Les montants d'une ligne de commande ne peuvent pas être négatifs."))

    def save(self, *args, **kwargs):
        if not self.total_ligne and self.prix_unitaire:
            self.total_ligne = Decimal(str(self.prix_unitaire)) * Decimal(str(self.quantite))
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantite}x {self.nom_produit_snapshot} ({self.total_ligne} FCFA)"


class LigneCommandeVariante(models.Model):
    """
    Snapshot de la variante sélectionnée pour une LigneCommande.
    Garantit l'immutabilité historique des choix du Client.
    """
    id = models.BigAutoField(primary_key=True)
    ligne_commande = models.OneToOneField(
        LigneCommande,
        on_delete=models.CASCADE,
        related_name='variante_snapshot',
        verbose_name=_('ligne de commande')
    )
    variante = models.ForeignKey(
        VarianteProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('variante d\'origine')
    )
    nom_variante_snapshot = models.CharField(_('nom variante (snapshot)'), max_length=150)
    prix_supplementaire_snapshot = models.DecimalField(
        _('prix supplémentaire snapshot (FCFA)'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = _('Variante Ligne de Commande')
        verbose_name_plural = _('Variantes Lignes de Commande')

    def __str__(self):
        return f"Variante '{self.nom_variante_snapshot}' pour {self.ligne_commande.nom_produit_snapshot}"


class LigneCommandeOption(models.Model):
    """
    Snapshot d'une option/sauce/supplément sélectionné pour une LigneCommande.
    Garantit l'immutabilité historique.
    """
    id = models.BigAutoField(primary_key=True)
    ligne_commande = models.ForeignKey(
        LigneCommande,
        on_delete=models.CASCADE,
        related_name='options_snapshot',
        verbose_name=_('ligne de commande')
    )
    option = models.ForeignKey(
        OptionProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('option d\'origine')
    )
    nom_option_snapshot = models.CharField(_('nom option (snapshot)'), max_length=150)
    type_option_snapshot = models.CharField(_('type option (snapshot)'), max_length=20, default='SAUCE')
    prix_supplementaire_snapshot = models.DecimalField(
        _('prix supplémentaire snapshot (FCFA)'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00')
    )

    class Meta:
        verbose_name = _('Option Ligne de Commande')
        verbose_name_plural = _('Options Lignes de Commande')

    def __str__(self):
        return f"Option '{self.nom_option_snapshot}' (+{self.prix_supplementaire_snapshot} FCFA)"


class AdresseLivraison(models.Model):
    """
    Adresse de livraison enregistrée dans le carnet d'adresses du Client.
    """
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='adresses_livraison',
        verbose_name=_('utilisateur')
    )
    titre = models.CharField(_('titre (ex: Domicile, Bureau)'), max_length=100, default='Domicile')
    adresse = models.CharField(_('adresse complète'), max_length=255)
    latitude = models.DecimalField(_('latitude'), max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(_('longitude'), max_digits=10, decimal_places=7, null=True, blank=True)
    instructions = models.TextField(_('instructions pour le livreur'), blank=True, default='')
    est_defaut = models.BooleanField(_('adresse par défaut'), default=False)
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Adresse de Livraison Client')
        verbose_name_plural = _('Adresses de Livraison Client')
        ordering = ['-est_defaut', '-date_creation']

    def __str__(self):
        return f"{self.titre} - {self.adresse} ({self.utilisateur.get_full_name()})"


class RepasPlanifie(models.Model):
    """
    Repas planifié par un Client AYYOU dans son planning personnel.
    """
    CRENEAU_MATIN = 'MATIN'
    CRENEAU_MIDI = 'MIDI'
    CRENEAU_SOIR = 'SOIR'
    CRENEAU_EN_CAS = 'EN_CAS'

    CHOIX_CRENEAUX = [
        (CRENEAU_MATIN, _('Petit-déjeuner')),
        (CRENEAU_MIDI, _('Déjeuner')),
        (CRENEAU_SOIR, _('Dîner')),
        (CRENEAU_EN_CAS, _('En-cas / Collation')),
    ]

    STATUT_PLANIFIE = 'PLANIFIE'
    STATUT_COMMANDE = 'COMMANDE'
    STATUT_ANNULE = 'ANNULE'

    CHOIX_STATUTS = [
        (STATUT_PLANIFIE, _('Planifié')),
        (STATUT_COMMANDE, _('Commande créée')),
        (STATUT_ANNULE, _('Annulé')),
    ]

    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='repas_planifies',
        verbose_name=_('client')
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='repas_planifies',
        verbose_name=_('produit planifié')
    )
    etablissement = models.ForeignKey(
        Etablissement,
        on_delete=models.CASCADE,
        related_name='repas_planifies',
        verbose_name=_('établissement')
    )
    variante = models.ForeignKey(
        VarianteProduit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='repas_planifies',
        verbose_name=_('variante choisie')
    )
    date_planifiee = models.DateField(_('date planifiée'), db_index=True)
    heure_planifiee = models.TimeField(_('heure planifiée'), null=True, blank=True)
    creneau = models.CharField(_('créneau du repas'), max_length=20, choices=CHOIX_CRENEAUX, default=CRENEAU_MIDI, db_index=True)
    statut = models.CharField(_('statut'), max_length=30, choices=CHOIX_STATUTS, default=STATUT_PLANIFIE, db_index=True)
    prix_total = models.DecimalField(_('prix total (FCFA)'), max_digits=10, decimal_places=2)
    quantite = models.PositiveIntegerField(_('quantité'), default=1)
    instructions = models.TextField(_('instructions spécifiques'), blank=True, default='')

    rappel_valide = models.BooleanField(_('rappel validé'), default=False)
    rappel_valide_at = models.DateTimeField(_('date de validation du rappel'), null=True, blank=True)
    rappel_reporte = models.BooleanField(_('rappel reporté'), default=False)
    rappel_reporte_at = models.DateTimeField(_('date de report du rappel'), null=True, blank=True)

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Repas Planifié')
        verbose_name_plural = _('Repas Planifiés')
        ordering = ['date_planifiee', 'creneau', 'id']
        indexes = [
            models.Index(fields=['utilisateur', 'date_planifiee']),
        ]

    def clean(self):
        super().clean()
        if self.quantite < 1:
            raise ValidationError(_("La quantité doit être supérieure ou égale à 1."))
        if self.prix_total < 0:
            raise ValidationError(_("Le prix ne peut pas être négatif."))

    def save(self, *args, **kwargs):
        if self.produit and not self.etablissement_id:
            self.etablissement = self.produit.etablissement
        if self.produit and not self.prix_total:
            prix = Decimal(str(self.produit.prix_base))
            if self.variante:
                prix += Decimal(str(self.variante.surcout_prix))
            self.prix_total = prix * Decimal(str(self.quantite))
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Repas '{self.produit.nom}' pour le {self.date_planifiee} ({self.get_creneau_display()}) - {self.utilisateur.get_full_name()}"
