from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.users.models import Utilisateur


class AuditLog(models.Model):
    """
    Journal d'audit infalsifiable des actions d'administration exécutées sur la console Super Admin AYYOU.
    Sécurité : Ne stocke jamais de mots de passe, clés d'API, tokens JWT ou codes OTP.
    """
    STATUT_SUCCESS = 'SUCCESS'
    STATUT_WARNING = 'WARNING'
    STATUT_FAILED = 'FAILED'

    CHOIX_STATUTS = [
        (STATUT_SUCCESS, _('Succès')),
        (STATUT_WARNING, _('Avertissement')),
        (STATUT_FAILED, _('Échec')),
    ]

    id = models.BigAutoField(primary_key=True)
    administrateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        verbose_name=_('administrateur')
    )
    admin_email = models.CharField(_('email administrateur'), max_length=255, blank=True, default='')
    action = models.CharField(_('action exécutée'), max_length=255)
    ressource = models.CharField(_('ressource ciblée'), max_length=255)
    resource_id = models.CharField(_('identifiant ressource'), max_length=100, blank=True, default='')
    ip_address = models.GenericIPAddressField(_('adresse IP'), null=True, blank=True)
    statut = models.CharField(_('statut'), max_length=20, choices=CHOIX_STATUTS, default=STATUT_SUCCESS)
    details = models.JSONField(_('détails complémentaires'), default=dict, blank=True)
    timestamp = models.DateTimeField(_('horodatage'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Journal d\'Audit')
        verbose_name_plural = _('Journaux d\'Audit')
        ordering = ['-timestamp']

    def __str__(self):
        admin_str = self.admin_email or (self.administrateur.get_full_name() if self.administrateur else 'Système')
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {admin_str} -> {self.action} ({self.ressource})"
