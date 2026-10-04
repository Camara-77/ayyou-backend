from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.users.models import Utilisateur


class Categorie(models.Model):
    """
    Catégories globales pour les plats et produits (ex: Plats Nationaux, Burgers, Viande, Brunch, Desserts).
    """
    id = models.BigAutoField(primary_key=True)
    slug = models.SlugField(_('slug'), max_length=100, unique=True, db_index=True)
    nom = models.CharField(_('nom de la catégorie'), max_length=150)
    icone = models.CharField(_('icône'), max_length=100, blank=True, default='')
    image_url = models.URLField(_('URL de l\'image'), max_length=500, blank=True, null=True)
    est_active = models.BooleanField(_('est active'), default=True)
    ordre = models.IntegerField(_('ordre d\'affichage'), default=0)
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Catégorie')
        verbose_name_plural = _('Catégories')
        ordering = ['ordre', 'nom']

    def __str__(self):
        return self.nom


class Etablissement(models.Model):
    """
    Établissement vendeur sur la plateforme AYYOU.
    Distingue explicitement les RESTAURANTS (établissement physique) des VENDEURS (activité à domicile).
    """
    TYPE_RESTAURANT = 'RESTAURANT'
    TYPE_VENDEUR = 'VENDEUR'
    CHOIX_TYPES = [
        (TYPE_RESTAURANT, _('Restaurant')),
        (TYPE_VENDEUR, _('Vendeur à domicile')),
    ]

    STATUT_OUVERT = 'open'
    STATUT_FERME = 'closed'
    CHOIX_STATUTS = [
        (STATUT_OUVERT, _('Ouvert')),
        (STATUT_FERME, _('Fermé')),
    ]

    id = models.BigAutoField(primary_key=True)
    nom = models.CharField(_('nom de l\'établissement'), max_length=200, db_index=True)
    type_etablissement = models.CharField(
        _('type d\'établissement'),
        max_length=30,
        choices=CHOIX_TYPES,
        default=TYPE_RESTAURANT,
        db_index=True
    )
    proprietaire = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='etablissements',
        verbose_name=_('propriétaire')
    )
    logo_url = models.URLField(_('URL du logo'), max_length=500, blank=True, null=True)
    couverture_url = models.URLField(_('URL de la photo de couverture'), max_length=500, blank=True, null=True)
    slogan = models.CharField(_('slogan'), max_length=255, blank=True, default='')
    description = models.TextField(_('description'), blank=True, default='')
    adresse = models.CharField(_('adresse'), max_length=255)
    latitude = models.DecimalField(_('latitude'), max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(_('longitude'), max_digits=10, decimal_places=7, null=True, blank=True)

    note_moyenne = models.DecimalField(_('note moyenne'), max_digits=3, decimal_places=2, default=0.00)
    nombre_avis = models.IntegerField(_('nombre d\'avis'), default=0)
    statut = models.CharField(_('statut'), max_length=20, choices=CHOIX_STATUTS, default=STATUT_OUVERT)
    heure_fermeture = models.CharField(_('heure de fermeture'), max_length=50, blank=True, default='23h30')
    telephone = models.CharField(_('téléphone'), max_length=30, blank=True, default='')
    specialite = models.CharField(_('spécialité'), max_length=150, blank=True, default='')
    nombre_videos = models.IntegerField(_('nombre de vidéos'), default=0)
    est_verifie = models.BooleanField(_('est vérifié par AYYOU'), default=False)

    STATUT_EN_ATTENTE = 'EN_ATTENTE'
    STATUT_VALIDE = 'VALIDE'
    STATUT_REFUSE = 'REFUSE'

    CHOIX_STATUT_VERIFICATION = [
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_VALIDE, _('Validé')),
        (STATUT_REFUSE, _('Refusé')),
    ]

    statut_verification = models.CharField(
        _('statut de vérification'),
        max_length=20,
        choices=CHOIX_STATUT_VERIFICATION,
        default=STATUT_EN_ATTENTE,
        db_index=True
    )

    STATUT_ABONNEMENT_INACTIF = 'INACTIF'
    STATUT_ABONNEMENT_EN_ATTENTE = 'EN_ATTENTE_PAIEMENT'
    STATUT_ABONNEMENT_ACTIF = 'ACTIF'
    STATUT_ABONNEMENT_EXPIRE = 'EXPIRE'

    CHOIX_STATUT_ABONNEMENT = [
        (STATUT_ABONNEMENT_INACTIF, _('Inactif')),
        (STATUT_ABONNEMENT_EN_ATTENTE, _('En attente de paiement')),
        (STATUT_ABONNEMENT_ACTIF, _('Actif')),
        (STATUT_ABONNEMENT_EXPIRE, _('Expiré')),
    ]

    statut_abonnement = models.CharField(
        _("statut d'abonnement"),
        max_length=30,
        choices=CHOIX_STATUT_ABONNEMENT,
        default=STATUT_ABONNEMENT_INACTIF,
        db_index=True
    )
    date_debut_abonnement = models.DateTimeField(_("date de début d'abonnement"), null=True, blank=True)
    date_expiration_abonnement = models.DateTimeField(_("date d'expiration d'abonnement"), null=True, blank=True, db_index=True)

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Établissement')
        verbose_name_plural = _('Établissements')
        ordering = ['-date_creation']

    def clean(self):
        super().clean()
        if self.statut_verification == self.STATUT_VALIDE:
            self.est_verifie = True
        else:
            self.est_verifie = False

    def save(self, *args, **kwargs):
        if self.pk is None and not self.date_debut_abonnement:
            from django.utils import timezone
            from apps.payments.services import PaymentService
            now = timezone.now()
            self.date_debut_abonnement = now
            self.date_expiration_abonnement = PaymentService.ajouter_un_mois_calendaire(now)
            self.statut_abonnement = self.STATUT_ABONNEMENT_ACTIF
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nom} ({self.get_type_etablissement_display()})"


class DocumentEtablissement(models.Model):
    """
    Documents justificatifs déposés par le Restaurant ou Vendeur (NINEA, Hygiène, CNI du gérant, etc.).
    """
    TYPE_REGISTRE_COMMERCE = 'REGISTRE_COMMERCE'
    TYPE_CERTIFICAT_HYGIENE = 'CERTIFICAT_HYGIENE'
    TYPE_CNI_GERANT = 'CNI_GERANT'
    TYPE_AUTRE = 'AUTRE'

    CHOIX_TYPE_DOCUMENT = [
        (TYPE_REGISTRE_COMMERCE, _("Registre de commerce / NINEA")),
        (TYPE_CERTIFICAT_HYGIENE, _("Certificat d'hygiène")),
        (TYPE_CNI_GERANT, _("CNI du gérant")),
        (TYPE_AUTRE, _("Autre")),
    ]

    STATUT_EN_ATTENTE = 'EN_ATTENTE'
    STATUT_VALIDE = 'VALIDE'
    STATUT_REFUSE = 'REFUSE'

    CHOIX_STATUT_DOCUMENT = [
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_VALIDE, _('Validé')),
        (STATUT_REFUSE, _('Refusé')),
    ]

    id = models.BigAutoField(primary_key=True)
    etablissement = models.ForeignKey(
        Etablissement,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('établissement')
    )
    type_document = models.CharField(
        _('type de document'),
        max_length=30,
        choices=CHOIX_TYPE_DOCUMENT
    )
    fichier_url_ou_reference = models.CharField(_('fichier URL ou référence'), max_length=500)
    statut = models.CharField(
        _('statut'),
        max_length=20,
        choices=CHOIX_STATUT_DOCUMENT,
        default=STATUT_EN_ATTENTE
    )
    date_verification = models.DateTimeField(_('date de vérification'), null=True, blank=True)
    commentaire = models.TextField(_('commentaire'), blank=True, default='')

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Document Établissement')
        verbose_name_plural = _('Documents Établissements')

    def __str__(self):
        return f"Document {self.get_type_document_display()} - {self.etablissement.nom}"


class Produit(models.Model):
    """
    Plat ou Produit proposé au catalogue Client.
    Gère la distinction entre le stock général et le stock alloué/réservé pour AYYOU.
    """
    id = models.BigAutoField(primary_key=True)
    etablissement = models.ForeignKey(
        Etablissement,
        on_delete=models.CASCADE,
        related_name='produits',
        verbose_name=_('établissement')
    )
    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='produits',
        verbose_name=_('catégorie')
    )
    nom = models.CharField(_('nom du produit'), max_length=200, db_index=True)
    description = models.TextField(_('description'), blank=True, default='')
    prix_base = models.DecimalField(_('prix de base (FCFA)'), max_digits=10, decimal_places=2)
    image_url = models.URLField(_('URL de l\'image principale'), max_length=500)
    images_galerie = models.JSONField(_('images de la galerie'), default=list, blank=True)
    est_disponible = models.BooleanField(_('est disponible'), default=True)

    # Stockage et allocation AYYOU
    stock_disponible = models.IntegerField(_('stock général disponible'), default=100)
    stock_ayyou_reserve = models.IntegerField(_('stock alloué à AYYOU'), default=50)

    temps_preparation = models.CharField(_('temps de préparation'), max_length=50, default='20-25 min')
    nombre_likes = models.IntegerField(_('nombre de likes'), default=0)
    tags = models.JSONField(_('tags'), default=list, blank=True)

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Produit / Plat')
        verbose_name_plural = _('Produits / Plats')
        ordering = ['-date_creation']

    def __str__(self):
        return f"{self.nom} - {self.etablissement.nom} ({self.prix_base} FCFA)"


class VarianteProduit(models.Model):
    """
    Variante ou portion d'un plat (ex: Classique 1 pers, Gourmand Tiof XL, Familial Teranga).
    Chaque variante possède son surcoût propre.
    """
    id = models.BigAutoField(primary_key=True)
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='variantes',
        verbose_name=_('produit')
    )
    titre = models.CharField(_('titre de la variante'), max_length=150)
    sous_titre = models.CharField(_('sous-titre / description'), max_length=255, blank=True, default='')
    surcout_prix = models.DecimalField(_('surcoût prix (FCFA)'), max_digits=10, decimal_places=2, default=0.00)
    est_requis = models.BooleanField(_('sélection obligatoire'), default=False)
    ordre = models.IntegerField(_('ordre'), default=0)

    class Meta:
        verbose_name = _('Variante de Produit')
        verbose_name_plural = _('Variantes de Produit')
        ordering = ['ordre', 'id']

    def __str__(self):
        return f"{self.titre} (+{self.surcout_prix} FCFA) - {self.produit.nom}"


class OptionProduit(models.Model):
    """
    Options et suppléments d'un plat (distingue les SAUCES des SUPPLÉMENTS payants).
    """
    TYPE_SAUCE = 'SAUCE'
    TYPE_SUPPLEMENT = 'SUPPLEMENT'
    CHOIX_TYPES = [
        (TYPE_SAUCE, _('Sauce')),
        (TYPE_SUPPLEMENT, _('Supplément')),
    ]

    id = models.BigAutoField(primary_key=True)
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name='options',
        verbose_name=_('produit')
    )
    type_option = models.CharField(_('type d\'option'), max_length=20, choices=CHOIX_TYPES, default=TYPE_SAUCE)
    titre = models.CharField(_('titre'), max_length=150)
    sous_titre = models.CharField(_('sous-titre'), max_length=255, blank=True, default='')
    surcout_prix = models.DecimalField(_('surcoût prix (FCFA)'), max_digits=10, decimal_places=2, default=0.00)
    est_inclus = models.BooleanField(_('inclus par défaut'), default=False)
    ordre = models.IntegerField(_('ordre'), default=0)

    class Meta:
        verbose_name = _('Option / Supplément Produit')
        verbose_name_plural = _('Options / Suppléments Produit')
        ordering = ['ordre', 'id']

    def __str__(self):
        return f"[{self.get_type_option_display()}] {self.titre} (+{self.surcout_prix} FCFA)"


class PublicationFeed(models.Model):
    """
    Contenu social / post média (image ou vidéo) d'un établissement affiché sur le Feed TikTok-style.
    Un produit peut être visuellement associé, mais n'est pas obligatoire.
    """
    TYPE_MEDIA_IMAGE = 'image'
    TYPE_MEDIA_VIDEO = 'video'
    CHOIX_MEDIAS = [
        (TYPE_MEDIA_IMAGE, _('Image')),
        (TYPE_MEDIA_VIDEO, _('Vidéo')),
    ]

    id = models.BigAutoField(primary_key=True)
    etablissement = models.ForeignKey(
        Etablissement,
        on_delete=models.CASCADE,
        related_name='publications',
        verbose_name=_('établissement')
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='publications',
        verbose_name=_('produit associé')
    )
    media_url = models.URLField(_('URL du média'), max_length=500)
    cloudinary_public_id = models.CharField(_('ID public Cloudinary'), max_length=255, blank=True, null=True)
    type_media = models.CharField(_('type de média'), max_length=10, choices=CHOIX_MEDIAS, default=TYPE_MEDIA_IMAGE)
    duree_video = models.CharField(_('durée vidéo (ex: 2:30)'), max_length=20, blank=True, default='')
    max_duree_secondes = models.IntegerField(_('durée max en secondes'), default=180)
    nombre_likes = models.IntegerField(_('nombre de likes'), default=0)
    nombre_partages = models.IntegerField(_('nombre de partages'), default=0)
    date_publication = models.DateTimeField(_('date de publication'), auto_now_add=True)

    class Meta:
        verbose_name = _('Publication Feed')
        verbose_name_plural = _('Publications Feed')
        ordering = ['-date_publication']

    def __str__(self):
        return f"Post {self.get_type_media_display()} - {self.etablissement.nom}"


class LikeProduit(models.Model):
    """
    Table de persistance des Likes clients sur les produits ou les publications du Feed.
    Assure l'unicité des Likes par utilisateur.
    """
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='likes_catalog',
        verbose_name=_('utilisateur')
    )
    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='likes',
        verbose_name=_('produit')
    )
    publication = models.ForeignKey(
        PublicationFeed,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='likes',
        verbose_name=_('publication feed')
    )
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Like Produit / Publication')
        verbose_name_plural = _('Likes Produits / Publications')
        constraints = [
            models.UniqueConstraint(
                fields=['utilisateur', 'produit'],
                name='unique_like_utilisateur_produit',
                condition=models.Q(produit__isnull=False)
            ),
            models.UniqueConstraint(
                fields=['utilisateur', 'publication'],
                name='unique_like_utilisateur_publication',
                condition=models.Q(publication__isnull=False)
            ),
        ]

    def clean(self):
        super().clean()
        if not self.produit and not self.publication:
            raise ValidationError(_("Un Like doit être associé à un Produit ou à une Publication Feed."))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        cible = self.produit.nom if self.produit else f"Post {self.publication_id}"
        return f"Like de {self.utilisateur.get_full_name()} sur {cible}"


class AbonnementEtablissement(models.Model):
    """
    Table de suivi des abonnements des clients aux établissements (Restaurants & Vendeurs).
    Modèle inspiré des réseaux sociaux (type TikTok / Instagram) permettant de suivre un établissement.
    """
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='abonnements_etablissements',
        verbose_name=_('utilisateur')
    )
    etablissement = models.ForeignKey(
        Etablissement,
        on_delete=models.CASCADE,
        related_name='abonnes',
        verbose_name=_('établissement')
    )
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Abonnement Établissement')
        verbose_name_plural = _('Abonnements Établissements')
        ordering = ['-date_creation']
        constraints = [
            models.UniqueConstraint(
                fields=['utilisateur', 'etablissement'],
                name='unique_abonnement_utilisateur_etablissement'
            )
        ]

    def __str__(self):
        return f"{self.utilisateur.get_full_name()} s'est abonné(e) à {self.etablissement.nom}"

