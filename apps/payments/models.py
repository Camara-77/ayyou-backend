from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import uuid
import datetime

from apps.orders.models import Commande


class Paiement(models.Model):
    """
    Modèle représentant une transaction de paiement AYYOU associée à une Commande.
    Supporte le cycle de vie complet d'un paiement indépendamment du prestataire externe.
    """

    # Méthodes de paiement
    METHODE_WAVE = 'WAVE'
    METHODE_ORANGE_MONEY = 'ORANGE_MONEY'
    METHODE_CARTE_BANCAIRE = 'CARTE_BANCAIRE'
    METHODE_CASH = 'CASH'
    METHODE_AUTRE = 'AUTRE'

    CHOIX_METHODES = [
        (METHODE_WAVE, _('Wave')),
        (METHODE_ORANGE_MONEY, _('Orange Money')),
        (METHODE_CARTE_BANCAIRE, _('Carte Bancaire')),
        (METHODE_CASH, _('Paiement à la livraison (Cash)')),
        (METHODE_AUTRE, _('Autre')),
    ]

    # Statuts de paiement
    STATUT_EN_ATTENTE = 'EN_ATTENTE'
    STATUT_INITIE = 'INITIE'
    STATUT_PAYE = 'PAYE'
    STATUT_ECHOUE = 'ECHOUE'
    STATUT_EXPIRE = 'EXPIRE'
    STATUT_ANNULE = 'ANNULE'

    CHOIX_STATUTS = [
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_INITIE, _('Initié')),
        (STATUT_PAYE, _('Payé')),
        (STATUT_ECHOUE, _('Échoué')),
        (STATUT_EXPIRE, _('Expiré')),
        (STATUT_ANNULE, _('Annulé')),
    ]

    TYPE_COMMANDE_CLIENT = 'COMMANDE_CLIENT'
    TYPE_ABONNEMENT_PRO = 'ABONNEMENT_PRO'

    CHOIX_TYPES_PAIEMENT = [
        (TYPE_COMMANDE_CLIENT, _('Commande Client')),
        (TYPE_ABONNEMENT_PRO, _('Abonnement PRO')),
    ]

    id = models.BigAutoField(primary_key=True)
    commande = models.ForeignKey(
        Commande,
        on_delete=models.CASCADE,
        related_name='paiements',
        verbose_name=_('commande'),
        null=True,
        blank=True
    )
    etablissement = models.ForeignKey(
        'catalog.Etablissement',
        on_delete=models.CASCADE,
        related_name='paiements_abonnement',
        verbose_name=_('établissement'),
        null=True,
        blank=True
    )
    type_paiement = models.CharField(
        _('type de paiement'),
        max_length=30,
        choices=CHOIX_TYPES_PAIEMENT,
        default=TYPE_COMMANDE_CLIENT,
        db_index=True
    )
    reference = models.CharField(
        _('référence interne AYYOU'),
        max_length=100,
        unique=True,
        blank=True,
        db_index=True
    )
    montant = models.DecimalField(
        _('montant du paiement (FCFA)'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    methode = models.CharField(
        _('méthode de paiement'),
        max_length=30,
        choices=CHOIX_METHODES,
        default=METHODE_WAVE,
        db_index=True
    )
    statut = models.CharField(
        _('statut du paiement'),
        max_length=30,
        choices=CHOIX_STATUTS,
        default=STATUT_EN_ATTENTE,
        db_index=True
    )
    transaction_externe = models.CharField(
        _('identifiant transaction externe'),
        max_length=255,
        blank=True,
        null=True,
        db_index=True
    )
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True, db_index=True)
    date_paiement = models.DateTimeField(_('date de paiement effectif'), blank=True, null=True)
    metadata = models.JSONField(_('données complémentaires'), default=dict, blank=True)

    class Meta:
        verbose_name = _('Paiement')
        verbose_name_plural = _('Paiements')
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['commande', 'statut']),
            models.Index(fields=['reference']),
        ]

    def clean(self):
        if not self.reference:
            self.reference = self.generer_reference()
        super().clean()
        if self.montant is not None and Decimal(str(self.montant)) <= Decimal('0.00'):
            raise ValidationError(_("Le montant d'un paiement doit être strictement supérieur à zéro."))

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generer_reference()
        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def generer_reference(cls) -> str:
        """
        Génère une référence de paiement unique AYYOU (ex: PAY-20260916-A1B2C3).
        """
        date_str = datetime.date.today().strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        return f"PAY-{date_str}-{suffix}"

    def marquer_comme_paye(self, transaction_externe=None):
        """
        Marque le paiement comme réussi et met à jour la date de paiement.
        """
        from django.utils import timezone
        self.statut = self.STATUT_PAYE
        self.date_paiement = timezone.now()
        if transaction_externe:
            self.transaction_externe = transaction_externe
        self.save(update_fields=['statut', 'date_paiement', 'transaction_externe'])

    def __str__(self):
        return f"Paiement {self.reference} ({self.get_methode_display()}) - {self.montant} FCFA [{self.get_statut_display()}]"


class Facture(models.Model):
    """
    Modèle représentant une Facture client officielle générée pour une Commande AYYOU.
    Conserve des snapshots immuables des informations financières et client au moment de l'émission.
    """
    id = models.BigAutoField(primary_key=True)
    commande = models.OneToOneField(
        Commande,
        on_delete=models.CASCADE,
        related_name='facture',
        verbose_name=_('commande associée')
    )
    paiement = models.ForeignKey(
        Paiement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='factures',
        verbose_name=_('paiement associé')
    )
    numero_facture = models.CharField(
        _('numéro de facture'),
        max_length=100,
        unique=True,
        blank=True,
        db_index=True
    )
    nom_client_snapshot = models.CharField(_('nom client (snapshot)'), max_length=150)
    telephone_client_snapshot = models.CharField(_('téléphone client (snapshot)'), max_length=30)
    adresse_livraison_snapshot = models.TextField(_('adresse de livraison (snapshot)'))

    montant_ht = models.DecimalField(_('montant hors taxes (FCFA)'), max_digits=12, decimal_places=2, default=Decimal('0.00'))
    frais_livraison = models.DecimalField(_('frais de livraison (FCFA)'), max_digits=10, decimal_places=2, default=Decimal('0.00'))
    montant_total = models.DecimalField(_('montant total TTC (FCFA)'), max_digits=12, decimal_places=2)

    details_lignes_snapshot = models.JSONField(_('détails des articles (snapshot)'), default=list, blank=True)
    est_payee = models.BooleanField(_('facture acquittée'), default=False)
    date_emission = models.DateTimeField(_('date d\'émission'), auto_now_add=True, db_index=True)
    date_paiement = models.DateTimeField(_('date de règlement'), null=True, blank=True)

    class Meta:
        verbose_name = _('Facture')
        verbose_name_plural = _('Factures')
        ordering = ['-date_emission']
        indexes = [
            models.Index(fields=['numero_facture']),
            models.Index(fields=['est_payee']),
        ]

    def clean(self):
        if not self.numero_facture:
            self.numero_facture = self.generer_numero_facture()
        super().clean()
        if self.montant_total is not None and Decimal(str(self.montant_total)) <= Decimal('0.00'):
            raise ValidationError(_("Le montant total d'une facture doit être strictement supérieur à zéro."))

    def save(self, *args, **kwargs):
        if not self.numero_facture:
            self.numero_facture = self.generer_numero_facture()

        if self.commande_id:
            if not self.nom_client_snapshot:
                self.nom_client_snapshot = self.commande.nom_destinataire or self.commande.utilisateur.get_full_name()
            if not self.telephone_client_snapshot:
                self.telephone_client_snapshot = self.commande.telephone_destinataire or self.commande.utilisateur.numero_telephone
            if not self.adresse_livraison_snapshot:
                self.adresse_livraison_snapshot = self.commande.adresse_livraison
            if not self.montant_total:
                self.montant_total = self.commande.total
            if not self.frais_livraison:
                self.frais_livraison = self.commande.frais_livraison
            if not self.montant_ht:
                self.montant_ht = self.commande.sous_total

        self.clean()
        super().save(*args, **kwargs)

    @classmethod
    def generer_numero_facture(cls) -> str:
        """
        Génère un numéro de facture unique AYYOU (ex: FAC-20260916-A1B2C3).
        """
        date_str = datetime.date.today().strftime('%Y%m%d')
        suffix = uuid.uuid4().hex[:6].upper()
        return f"FAC-{date_str}-{suffix}"

    def __str__(self):
        statut = "Acquittée" if self.est_payee else "Non payée"
        return f"Facture {self.numero_facture} ({self.montant_total} FCFA) - {statut}"


class Payout(models.Model):
    """
    Modèle représentant un versement/retrait de gains pour un livreur AYYOU.
    """
    STATUT_EN_ATTENTE = 'EN_ATTENTE'
    STATUT_TRAITE = 'TRAITE'
    STATUT_ECHOUE = 'ECHOUE'

    CHOIX_STATUTS = [
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_TRAITE, _('Traité')),
        (STATUT_ECHOUE, _('Échoué')),
    ]

    id = models.BigAutoField(primary_key=True)
    livreur = models.ForeignKey(
        'users.ProfilLivreur',
        on_delete=models.CASCADE,
        related_name='payouts',
        verbose_name=_('livreur')
    )
    montant = models.DecimalField(
        _('montant du versement (FCFA)'),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    methode = models.CharField(
        _('méthode de retrait'),
        max_length=50,
        default='WAVE'
    )
    statut = models.CharField(
        _('statut du versement'),
        max_length=30,
        choices=CHOIX_STATUTS,
        default=STATUT_EN_ATTENTE,
        db_index=True
    )
    date_demande = models.DateTimeField(_('date de demande'), auto_now_add=True, db_index=True)
    date_traitement = models.DateTimeField(_('date de traitement'), null=True, blank=True)
    reference = models.CharField(_('référence du versement'), max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name = _('Payout Livreur')
        verbose_name_plural = _('Payouts Livreurs')
        ordering = ['-date_demande']

    def save(self, *args, **kwargs):
        if not self.reference:
            date_str = datetime.date.today().strftime('%Y%m%d')
            suffix = uuid.uuid4().hex[:6].upper()
            self.reference = f"PO-{date_str}-{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Payout {self.reference} - {self.livreur} - {self.montant} FCFA [{self.statut}]"


class AbonnementPro(models.Model):
    """
    Enregistre chaque cycle d'abonnement PRO souscrit ou renouvelé par un Restaurant ou Vendeur (10 000 FCFA / mois).
    """
    STATUT_PAYE = 'PAYE'
    STATUT_EXPIRE = 'EXPIRE'
    STATUT_ANNULE = 'ANNULE'

    CHOIX_STATUTS = [
        (STATUT_PAYE, _('Payé / Actif')),
        (STATUT_EXPIRE, _('Expiré')),
        (STATUT_ANNULE, _('Annulé')),
    ]

    id = models.BigAutoField(primary_key=True)
    etablissement = models.ForeignKey(
        'catalog.Etablissement',
        on_delete=models.CASCADE,
        related_name='abonnements_pro',
        verbose_name=_('établissement')
    )
    paiement = models.OneToOneField(
        Paiement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='abonnement_pro',
        verbose_name=_('paiement associé')
    )
    montant = models.DecimalField(
        _('montant de l\'abonnement (FCFA)'),
        max_digits=10,
        decimal_places=2,
        default=Decimal('10000.00')
    )
    date_debut = models.DateTimeField(_('date de début'))
    date_expiration = models.DateTimeField(_('date d\'expiration'), db_index=True)
    statut = models.CharField(_('statut'), max_length=20, choices=CHOIX_STATUTS, default=STATUT_PAYE, db_index=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Abonnement PRO')
        verbose_name_plural = _('Abonnements PRO')
        ordering = ['-created_at']

    def __str__(self):
        return f"Abonnement PRO #{self.id} - {self.etablissement.nom} (Jusqu'au {self.date_expiration.strftime('%d/%m/%Y')})"


class FactureAbonnement(models.Model):
    """
    Facture comptable officielle émise pour un paiement d'abonnement PRO partenaire.
    """
    id = models.BigAutoField(primary_key=True)
    numero_facture = models.CharField(_('numéro de facture'), max_length=100, unique=True, db_index=True)
    abonnement = models.OneToOneField(
        AbonnementPro,
        on_delete=models.CASCADE,
        related_name='facture',
        verbose_name=_('abonnement associé')
    )
    etablissement = models.ForeignKey(
        'catalog.Etablissement',
        on_delete=models.CASCADE,
        related_name='factures_abonnement',
        verbose_name=_('établissement')
    )
    nom_etablissement_snapshot = models.CharField(_('nom établissement (snapshot)'), max_length=255)
    type_etablissement_snapshot = models.CharField(_('type établissement (snapshot)'), max_length=50)
    nom_proprietaire_snapshot = models.CharField(_('nom propriétaire (snapshot)'), max_length=255)
    email_proprietaire_snapshot = models.CharField(_('email propriétaire (snapshot)'), max_length=255)
    montant_ht = models.DecimalField(_('montant HT'), max_digits=10, decimal_places=2, default=Decimal('10000.00'))
    montant_total = models.DecimalField(_('montant total (FCFA)'), max_digits=10, decimal_places=2, default=Decimal('10000.00'))
    date_emission = models.DateTimeField(_('date d\'émission'), auto_now_add=True)

    class Meta:
        verbose_name = _('Facture Abonnement PRO')
        verbose_name_plural = _('Factures Abonnements PRO')
        ordering = ['-date_emission']

    def save(self, *args, **kwargs):
        if not self.numero_facture:
            date_str = datetime.date.today().strftime('%Y%m')
            suffix = uuid.uuid4().hex[:6].upper()
            self.numero_facture = f"FAC-PRO-{date_str}-{suffix}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Facture PRO {self.numero_facture} - {self.nom_etablissement_snapshot} (10 000 FCFA)"


