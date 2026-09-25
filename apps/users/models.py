from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re


class UtilisateurManager(BaseUserManager):
    """
    Gestionnaire personnalisé pour le modèle Utilisateur AYYOU.
    Permet la création d'utilisateurs et de superutilisateurs avec email et téléphone uniques.
    """

    def create_user(self, email, numero_telephone, password=None, **extra_fields):
        if not email:
            raise ValueError(_("L'adresse email est obligatoire."))
        if not numero_telephone:
            raise ValueError(_("Le numéro de téléphone est obligatoire."))

        email = self.normalize_email(email).lower()
        numero_telephone = numero_telephone.strip()

        user = self.model(
            email=email,
            numero_telephone=numero_telephone,
            **extra_fields
        )

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, numero_telephone, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('est_actif', True)
        extra_fields.setdefault('est_verifie', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_("Le superutilisateur doit avoir is_staff=True."))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_("Le superutilisateur doit avoir is_superuser=True."))

        return self.create_user(email, numero_telephone, password, **extra_fields)


class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """
    Modèle utilisateur central pour le système d'identité AYYOU.
    Remplace le modèle User Django par défaut via AUTH_USER_MODEL.
    """
    id = models.BigAutoField(primary_key=True)
    email = models.EmailField(_('adresse email'), unique=True, db_index=True)
    numero_telephone = models.CharField(_('numéro de téléphone'), max_length=30, unique=True, db_index=True)
    prenom = models.CharField(_('prénom'), max_length=150)
    nom = models.CharField(_('nom de famille'), max_length=150)

    est_actif = models.BooleanField(_('est actif'), default=True)
    est_verifie = models.BooleanField(_('est vérifié'), default=False)
    is_staff = models.BooleanField(_('statut équipe admin'), default=False)

    derniere_connexion = models.DateTimeField(_('dernière connexion'), null=True, blank=True)
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    objects = UtilisateurManager()

    MODE_CLIENT = 'CLIENT'
    MODE_LIVREUR = 'LIVREUR'

    CHOIX_MODE_ACTIF = [
        (MODE_CLIENT, _('Client')),
        (MODE_LIVREUR, _('Livreur')),
    ]

    mode_actif = models.CharField(
        _('mode actif'),
        max_length=20,
        choices=CHOIX_MODE_ACTIF,
        default=MODE_CLIENT
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['numero_telephone', 'prenom', 'nom']


    class Meta:
        verbose_name = _('Utilisateur')
        verbose_name_plural = _('Utilisateurs')
        ordering = ['-date_creation']

    def clean(self):
        super().clean()
        if self.email:
            self.email = self.email.strip().lower()
        if self.numero_telephone:
            self.numero_telephone = self.numero_telephone.strip()

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return f"{self.prenom} {self.nom}".strip()

    def get_short_name(self):
        return self.prenom

    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"


class ProfilClient(models.Model):
    """
    Profil spécifique au rôle Client.
    Séparé de l'identité principale Utilisateur (1 ─── 1).
    """
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='profil_client',
        verbose_name=_('utilisateur')
    )
    photo_avatar = models.URLField(_('photo d\'avatar'), max_length=500, blank=True, null=True)
    adresse_principale = models.CharField(_('adresse principale'), max_length=255, blank=True, default='')
    latitude = models.DecimalField(_('latitude'), max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(_('longitude'), max_digits=10, decimal_places=7, null=True, blank=True)
    date_naissance = models.DateField(_('date de naissance'), null=True, blank=True)
    notifications_activees = models.BooleanField(_('notifications activées'), default=True)

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Profil Client')
        verbose_name_plural = _('Profils Clients')

    def __str__(self):
        return f"Profil Client de {self.utilisateur.get_full_name()}"


class Role(models.Model):
    """
    Rôles métier disponibles dans la plateforme AYYOU.
     Extensible pour les phases ultérieures (CLIENT, RESTAURANT, VENDEUR, LIVREUR, ADMINISTRATEUR).
    """
    CLIENT = 'CLIENT'
    RESTAURANT = 'RESTAURANT'
    VENDEUR = 'VENDEUR'
    LIVREUR = 'LIVREUR'
    ADMINISTRATEUR = 'ADMINISTRATEUR'

    CHOIX_ROLES = [
        (CLIENT, _('Client')),
        (RESTAURANT, _('Restaurant')),
        (VENDEUR, _('Vendeur')),
        (LIVREUR, _('Livreur')),
        (ADMINISTRATEUR, _('Administrateur')),
    ]

    id = models.BigAutoField(primary_key=True)
    nom = models.CharField(_('nom du rôle'), max_length=50, choices=CHOIX_ROLES, unique=True)
    description = models.TextField(_('description'), blank=True)
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Rôle')
        verbose_name_plural = _('Rôles')

    def __str__(self):
        return self.get_nom_display()


class UtilisateurRole(models.Model):
    """
    Table d'association explicite entre Utilisateur et Role (N ─── N).
    Contrainte d'unicité empêchant d'attribuer deux fois le même rôle à un utilisateur.
    """
    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='roles_attribues',
        verbose_name=_('utilisateur')
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name='utilisateurs_lies',
        verbose_name=_('rôle')
    )
    date_attribution = models.DateTimeField(_('date d\'attribution'), auto_now_add=True)

    class Meta:
        verbose_name = _('Rôle Utilisateur')
        verbose_name_plural = _('Rôles Utilisateurs')
        constraints = [
            models.UniqueConstraint(
                fields=['utilisateur', 'role'],
                name='unique_utilisateur_role'
            )
        ]

    def __str__(self):
        return f"{self.utilisateur.get_full_name()} -> {self.role.get_nom_display()}"


class ProfilLivreur(models.Model):
    """
    Profil spécifique au rôle Livreur AYYOU Pro.
    Contient le statut de vérification, la disponibilité et le véhicule.
    """
    STATUT_EN_ATTENTE = 'EN_ATTENTE'
    STATUT_VALIDE = 'VALIDE'
    STATUT_REFUSE = 'REFUSE'

    CHOIX_STATUT_VERIFICATION = [
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_VALIDE, _('Validé')),
        (STATUT_REFUSE, _('Refusé')),
    ]

    VEHICULE_MOTO = 'MOTO'
    VEHICULE_VOITURE = 'VOITURE'
    VEHICULE_VELO = 'VELO'
    VEHICULE_AUTRE = 'AUTRE'

    CHOIX_TYPE_VEHICULE = [
        (VEHICULE_MOTO, _('Moto')),
        (VEHICULE_VOITURE, _('Voiture')),
        (VEHICULE_VELO, _('Vélo')),
        (VEHICULE_AUTRE, _('Autre')),
    ]

    id = models.BigAutoField(primary_key=True)
    utilisateur = models.OneToOneField(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='profil_livreur',
        verbose_name=_('utilisateur')
    )
    statut_verification = models.CharField(
        _('statut de vérification'),
        max_length=20,
        choices=CHOIX_STATUT_VERIFICATION,
        default=STATUT_EN_ATTENTE,
        db_index=True
    )
    est_disponible = models.BooleanField(_('est disponible'), default=False)
    latitude_actuelle = models.DecimalField(_('latitude actuelle'), max_digits=10, decimal_places=7, null=True, blank=True)
    longitude_actuelle = models.DecimalField(_('longitude actuelle'), max_digits=10, decimal_places=7, null=True, blank=True)
    date_derniere_position = models.DateTimeField(_('date dernière position'), null=True, blank=True)

    type_vehicule = models.CharField(
        _('type de véhicule'),
        max_length=20,
        choices=CHOIX_TYPE_VEHICULE,
        default=VEHICULE_MOTO
    )
    marque = models.CharField(_('marque'), max_length=100, blank=True, default='')
    modele = models.CharField(_('modèle'), max_length=100, blank=True, default='')
    immatriculation = models.CharField(_('immatriculation'), max_length=50, blank=True, default='')

    photo_avatar = models.URLField(_("photo d'avatar"), max_length=500, blank=True, null=True)
    date_expiration_assurance = models.DateField(_("date d'expiration assurance"), null=True, blank=True)
    statut_assurance = models.CharField(_("statut de l'assurance"), max_length=30, blank=True, default='CONFORME')
    equipements_certifies = models.CharField(_('équipements certifiés'), max_length=255, blank=True, default='')
    secteur_intervention = models.CharField(_("secteur d'intervention"), max_length=255, blank=True, default='')
    type_compte_reversement = models.CharField(_('type de compte reversement'), max_length=100, blank=True, default='')
    numero_reversement = models.CharField(_('numéro de compte reversement'), max_length=50, blank=True, default='')
    comptes_reversement = models.JSONField(_('comptes de reversement'), default=list, blank=True)

    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)
    date_modification = models.DateTimeField(_('date de modification'), auto_now=True)

    @property
    def matricule(self) -> str:
        return f"#AY-{self.id + 7700:04d}"

    class Meta:
        verbose_name = _('Profil Livreur')
        verbose_name_plural = _('Profils Livreurs')

    def clean(self):
        super().clean()
        if self.est_disponible and self.statut_verification != self.STATUT_VALIDE:
            raise ValidationError(
                _("Un livreur ne peut être disponible que si son profil est validé par un administrateur.")
            )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profil Livreur de {self.utilisateur.get_full_name()} ({self.get_statut_verification_display()})"


class DocumentLivreur(models.Model):
    """
    Documents justificatifs déposés par le Livreur (pièce d'identité, permis, carte grise, etc.).
    """
    TYPE_PIECE_IDENTITE = 'PIECE_IDENTITE'
    TYPE_PERMIS_CONDUIRE = 'PERMIS_CONDUIRE'
    TYPE_CARTE_GRISE = 'CARTE_GRISE'
    TYPE_AUTRE = 'AUTRE'

    CHOIX_TYPE_DOCUMENT = [
        (TYPE_PIECE_IDENTITE, _("Pièce d'identité")),
        (TYPE_PERMIS_CONDUIRE, _('Permis de conduire')),
        (TYPE_CARTE_GRISE, _('Carte grise')),
        (TYPE_AUTRE, _('Autre')),
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
    profil_livreur = models.ForeignKey(
        ProfilLivreur,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name=_('profil livreur')
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
        verbose_name = _('Document Livreur')
        verbose_name_plural = _('Documents Livreurs')

    def __str__(self):
        return f"Document {self.get_type_document_display()} - {self.profil_livreur.utilisateur.get_full_name()}"

