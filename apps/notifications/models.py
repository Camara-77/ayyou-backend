from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.users.models import Utilisateur


class Notification(models.Model):
    """
    Modèle central pour les notifications multi-canaux (In-App, Email, WhatsApp) AYYOU.
    Stocke l'historique des alertes destinées à un utilisateur (Client, Livreur, Marchand, Admin).
    """
    # Types de notification
    TYPE_AUTHENTICATION = 'AUTHENTICATION'
    TYPE_ORDER = 'ORDER'
    TYPE_DELIVERY = 'DELIVERY'
    TYPE_PRO_VALIDATION = 'PRO_VALIDATION'
    TYPE_SUBSCRIPTION = 'SUBSCRIPTION'
    TYPE_SYSTEM = 'SYSTEM'

    CHOIX_TYPES_NOTIFICATION = [
        (TYPE_AUTHENTICATION, _('Authentification / OTP')),
        (TYPE_ORDER, _('Commande')),
        (TYPE_DELIVERY, _('Livraison')),
        (TYPE_PRO_VALIDATION, _('Validation PRO')),
        (TYPE_SUBSCRIPTION, _('Abonnement PRO')),
        (TYPE_SYSTEM, _('Système')),
    ]

    # Canaux de diffusion
    CANAL_IN_APP = 'IN_APP'
    CANAL_EMAIL = 'EMAIL'
    CANAL_WHATSAPP = 'WHATSAPP'

    CHOIX_CANAUX = [
        (CANAL_IN_APP, _('In-App')),
        (CANAL_EMAIL, _('Email')),
        (CANAL_WHATSAPP, _('WhatsApp')),
    ]

    # Statuts de notification
    STATUT_EN_ATTENTE = 'EN_ATTENTE'
    STATUT_ENVOYEE = 'ENVOYEE'
    STATUT_ECHEC = 'ECHEC'
    STATUT_LU = 'LU'

    CHOIX_STATUTS = [
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_ENVOYEE, _('Envoyée')),
        (STATUT_ECHEC, _('Échec')),
        (STATUT_LU, _('Lue')),
    ]

    id = models.BigAutoField(primary_key=True)
    utilisateur = models.ForeignKey(
        Utilisateur,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('destinataire')
    )
    type_notification = models.CharField(
        _('type de notification'),
        max_length=50,
        choices=CHOIX_TYPES_NOTIFICATION,
        default=TYPE_SYSTEM,
        db_index=True
    )
    canal = models.CharField(
        _('canal de diffusion'),
        max_length=30,
        choices=CHOIX_CANAUX,
        default=CANAL_IN_APP,
        db_index=True
    )
    titre = models.CharField(_('titre'), max_length=255)
    message = models.TextField(_('contenu / message'))
    statut = models.CharField(
        _('statut d\'envoi'),
        max_length=30,
        choices=CHOIX_STATUTS,
        default=STATUT_ENVOYEE,
        db_index=True
    )

    est_lu = models.BooleanField(_('est lue'), default=False, db_index=True)
    date_lecture = models.DateTimeField(_('date de lecture'), null=True, blank=True)

    # Références métier découplées (ex: 'Commande', 'AYY-20260919-X123')
    reference_type = models.CharField(_('type de référence métier'), max_length=50, blank=True, default='')
    reference_id = models.CharField(_('identifiant référence métier'), max_length=100, blank=True, default='')
    metadata = models.JSONField(_('métadonnées complémentaires'), default=dict, blank=True)

    created_at = models.DateTimeField(_('date de création'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Notification')
        verbose_name_plural = _('Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['utilisateur', 'est_lu']),
            models.Index(fields=['utilisateur', '-created_at']),
        ]

    def marquer_comme_lu(self) -> None:
        """
        Marque la notification comme lue de manière idempotente.
        """
        if not self.est_lu:
            self.est_lu = True
            self.statut = self.STATUT_LU
            self.date_lecture = timezone.now()
            self.save(update_fields=['est_lu', 'statut', 'date_lecture', 'updated_at'])

    def __str__(self):
        statut_str = "Lue" if self.est_lu else "Non lue"
        return f"[{self.get_canal_display()}] {self.titre} -> {self.utilisateur.get_full_name()} ({statut_str})"
