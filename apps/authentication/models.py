from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class VerificationOTP(models.Model):
    """
    Modèle de gestion des codes de vérification OTP (SMS / Téléphone & Réinitialisation mot de passe).
    """
    VERIFICATION_TELEPHONE = 'VERIFICATION_TELEPHONE'
    REINITIALISATION_MOT_DE_PASSE = 'REINITIALISATION_MOT_DE_PASSE'

    CHOIX_TYPES_VERIFICATION = [
        (VERIFICATION_TELEPHONE, _('Vérification du numéro de téléphone')),
        (REINITIALISATION_MOT_DE_PASSE, _('Réinitialisation du mot de passe')),
    ]

    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        'users.Utilisateur',
        on_delete=models.CASCADE,
        related_name='verifications_otp',
        verbose_name=_('utilisateur')
    )
    code = models.CharField(_('code OTP'), max_length=6)
    type_verification = models.CharField(
        _('type de vérification'),
        max_length=50,
        choices=CHOIX_TYPES_VERIFICATION,
        default=VERIFICATION_TELEPHONE
    )
    date_expiration = models.DateTimeField(_('date d\'expiration'))
    nombre_tentatives = models.IntegerField(_('nombre de tentatives'), default=0)
    est_utilise = models.BooleanField(_('est utilisé'), default=False)
    date_creation = models.DateTimeField(_('date de création'), auto_now_add=True)

    class Meta:
        verbose_name = _('Vérification OTP')
        verbose_name_plural = _('Vérifications OTP')
        ordering = ['-date_creation']

    def est_expire(self):
        """Vérifie si le code OTP a dépassé sa date d'expiration."""
        return timezone.now() > self.date_expiration

    def incrementer_tentatives(self):
        """Incrémente le compteur de tentatives de saisie de l'OTP."""
        self.nombre_tentatives += 1
        self.save(update_fields=['nombre_tentatives'])

    def __str__(self):
        return f"OTP ({self.type_verification}) pour {self.utilisateur.email}"
