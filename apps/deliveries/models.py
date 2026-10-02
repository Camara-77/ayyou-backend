from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Commande
from apps.users.models import ProfilLivreur


class Livraison(models.Model):
    """
    Modèle du domaine Livraison AYYOU.
    Stocke le suivi de livraison, le token QR Code sécurisé et le code de validation à 6 chiffres.
    Chaque Commande validée et payée est associée à une unique Livraison.
    """
    STATUT_EN_ATTENTE = 'EN_ATTENTE'
    STATUT_AFFECTEE = 'AFFECTEE'
    STATUT_ACCEPTEE = 'ACCEPTEE'
    STATUT_ARRIVE_RESTAURANT = 'ARRIVE_RESTAURANT'
    STATUT_EN_PREPARATION = 'EN_PREPARATION'
    STATUT_PRETE = 'PRETE'
    STATUT_EN_LIVRAISON = 'EN_LIVRAISON'
    STATUT_LIVREE = 'LIVREE'
    STATUT_ANNULEE = 'ANNULEE'

    CHOIX_STATUTS = [
        (STATUT_EN_ATTENTE, _('En attente')),
        (STATUT_AFFECTEE, _('Affectée')),
        (STATUT_ACCEPTEE, _('Acceptée')),
        (STATUT_ARRIVE_RESTAURANT, _('Arrivé au restaurant')),
        (STATUT_EN_PREPARATION, _('En préparation')),
        (STATUT_PRETE, _('Prête')),
        (STATUT_EN_LIVRAISON, _('En livraison')),
        (STATUT_LIVREE, _('Livrée')),
        (STATUT_ANNULEE, _('Annulée')),
    ]

    METHODE_QR_CODE = 'QR_CODE'
    METHODE_CODE_VALIDATION = 'CODE_VALIDATION'

    CHOIX_METHODES_VALIDATION = [
        (METHODE_QR_CODE, _('Scan QR Code')),
        (METHODE_CODE_VALIDATION, _('Code de validation à 6 chiffres')),
    ]

    id = models.BigAutoField(primary_key=True)
    commande = models.OneToOneField(
        Commande,
        on_delete=models.CASCADE,
        related_name='livraison',
        verbose_name=_('commande')
    )
    livreur = models.ForeignKey(
        ProfilLivreur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='livraisons',
        verbose_name=_('livreur')
    )

    statut = models.CharField(
        _('statut de la livraison'),
        max_length=30,
        choices=CHOIX_STATUTS,
        default=STATUT_EN_ATTENTE,
        db_index=True
    )
    token_qr = models.CharField(
        _('token QR Code'),
        max_length=128,
        unique=True,
        db_index=True
    )
    code_validation = models.CharField(
        _('code de validation (4 chiffres)'),
        max_length=4,
        db_index=True
    )
    est_validee = models.BooleanField(_('est validée'), default=False)
    methode_validation = models.CharField(
        _('méthode de validation'),
        max_length=30,
        choices=CHOIX_METHODES_VALIDATION,
        null=True,
        blank=True
    )
    date_validation = models.DateTimeField(_('date de validation'), null=True, blank=True)
    date_attribution = models.DateTimeField(_("date d'attribution"), null=True, blank=True)
    phase_attribution = models.IntegerField(_("phase d'attribution"), default=1)
    propositions_livreurs = models.JSONField(_("propositions livreurs"), default=dict, blank=True)
    created_at = models.DateTimeField(_('date de création'), auto_now_add=True)
    updated_at = models.DateTimeField(_('date de modification'), auto_now=True)

    class Meta:
        verbose_name = _('Livraison')
        verbose_name_plural = _('Livraisons')
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.code_validation and (len(self.code_validation) != 4 or not self.code_validation.isdigit()):
            raise ValidationError(_("Le code de validation doit comporter exactement 4 chiffres."))

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Livraison #{self.id} pour Commande {self.commande.numero_commande} ({self.get_statut_display()})"
