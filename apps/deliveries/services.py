import random
import secrets
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Commande
from apps.deliveries.models import Livraison


class DeliveryService:
    """
    Service métier du domaine Livraison AYYOU.
    Gère la création de la livraison, la génération du token QR Code sécurisé,
    du code de validation à 6 chiffres, l'affectation des missions et le cycle de vie de livraison.
    """

    @staticmethod
    @transaction.atomic
    def creer_livraison(commande: Commande) -> Livraison:
        """
        Génère automatiquement une fiche de Livraison avec QR Token et Code de validation à 6 chiffres
        lorsqu'une commande est confirmée et payée.
        """
        if hasattr(commande, 'livraison') and commande.livraison:
            return commande.livraison

        # Token QR Code imprévisible et sécurisé (ne contient aucune donnée personnelle sensible)
        token_qr = f"AYYOU-DELIVERY-{secrets.token_hex(16)}"
        while Livraison.objects.filter(token_qr=token_qr).exists():
            token_qr = f"AYYOU-DELIVERY-{secrets.token_hex(16)}"

        # Code de validation à 6 chiffres aléatoire
        code_validation = f"{random.randint(100000, 999999)}"

        livraison = Livraison.objects.create(
            commande=commande,
            token_qr=token_qr,
            code_validation=code_validation,
            statut=Livraison.STATUT_EN_ATTENTE
        )
        return livraison

    @staticmethod
    @transaction.atomic
    def accepter_mission(livraison_id: int, profil_livreur) -> Livraison:
        """
        Permet à un livreur validé et disponible d'accepter de manière atomique une livraison disponible.
        Utilise select_for_update() pour éviter les courses concurrentes entre deux livreurs.
        """
        if not profil_livreur or profil_livreur.statut_verification != 'VALIDE':
            raise ValidationError(_("Seul un livreur validé par un administrateur peut accepter une mission."))

        if not profil_livreur.est_disponible:
            raise ValidationError(_("Vous devez être marqué comme disponible pour pouvoir accepter des missions."))

        try:
            livraison = Livraison.objects.select_for_update().get(pk=livraison_id)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Livraison introuvable."))

        if livraison.livreur is not None:
            raise ValidationError(_("Cette mission a déjà été acceptée par un autre livreur."))

        if livraison.statut in [Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]:
            raise ValidationError(_("Impossible d'accepter une livraison terminée ou annulée."))

        livraison.livreur = profil_livreur
        livraison.statut = Livraison.STATUT_ACCEPTEE
        livraison.save(update_fields=['livreur', 'statut', 'updated_at'])

        # Mise à jour synchronisée de la date de modification de la commande
        commande = livraison.commande
        if commande:
            commande.save(update_fields=['date_modification'])

        return livraison

    @staticmethod
    @transaction.atomic
    def recuperer_commande(livraison_id: int, profil_livreur) -> Livraison:
        """
        Permet au livreur affecté de déclarer qu'il a récupéré la commande auprès du restaurant/vendeur.
        Passe la livraison et la commande à l'état EN_LIVRAISON.
        """
        if not profil_livreur or profil_livreur.statut_verification != 'VALIDE':
            raise ValidationError(_("Seul un livreur validé peut effectuer cette action."))

        try:
            livraison = Livraison.objects.select_for_update().get(pk=livraison_id)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Livraison introuvable."))

        if livraison.livreur != profil_livreur:
            raise ValidationError(_("Cette livraison n'est pas affectée à votre compte."))

        if livraison.statut in [Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]:
            raise ValidationError(_("Impossible de récupérer une commande annulée ou déjà livrée."))

        livraison.statut = Livraison.STATUT_EN_LIVRAISON
        livraison.save(update_fields=['statut', 'updated_at'])

        # Mise à jour synchronisée de la commande et des sous-commandes
        commande = livraison.commande
        if commande:
            commande.statut = Commande.STATUT_EN_LIVRAISON
            commande.save(update_fields=['statut', 'date_modification'])
            commande.sous_commandes.update(statut=Commande.STATUT_EN_LIVRAISON)

        return livraison

    @staticmethod
    @transaction.atomic
    def valider_par_qr(token_qr: str, utilisateur=None) -> Livraison:
        """
        Valide la restitution de la commande par scan du QR Code (usage unique).
        """
        if not token_qr:
            raise ValidationError(_("Le token QR Code est obligatoire."))

        try:
            livraison = Livraison.objects.select_for_update().get(token_qr=token_qr)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Token QR Code invalide ou inexistant."))

        if livraison.est_validee:
            raise ValidationError(_("Cette livraison a déjà été validée."))

        if livraison.statut == Livraison.STATUT_ANNULEE:
            raise ValidationError(_("Impossible de valider une livraison annulée."))

        livraison.est_validee = True
        livraison.methode_validation = Livraison.METHODE_QR_CODE
        livraison.date_validation = timezone.now()
        livraison.statut = Livraison.STATUT_LIVREE
        livraison.save(update_fields=['est_validee', 'methode_validation', 'date_validation', 'statut', 'updated_at'])

        # Mise à jour synchronisée de la commande et des sous-commandes
        commande = livraison.commande
        commande.statut = Commande.STATUT_LIVREE
        commande.save(update_fields=['statut', 'date_modification'])
        commande.sous_commandes.update(statut=Commande.STATUT_LIVREE)

        return livraison

    @staticmethod
    @transaction.atomic
    def valider_par_code(commande_id: int, code_validation: str, utilisateur=None) -> Livraison:
        """
        Valide la restitution de la commande via le code de validation à 6 chiffres transmis par le client.
        """
        if not commande_id:
            raise ValidationError(_("L'identifiant de la commande est obligatoire."))

        if not code_validation:
            raise ValidationError(_("Le code de validation est obligatoire."))

        try:
            livraison = Livraison.objects.select_for_update().get(commande_id=commande_id)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Livraison introuvable pour cette commande."))

        if livraison.est_validee:
            raise ValidationError(_("Cette livraison a déjà été validée."))

        if livraison.statut == Livraison.STATUT_ANNULEE:
            raise ValidationError(_("Impossible de valider une livraison annulée."))

        if livraison.code_validation.strip() != code_validation.strip():
            raise ValidationError(_("Code de validation incorrect."))

        livraison.est_validee = True
        livraison.methode_validation = Livraison.METHODE_CODE_VALIDATION
        livraison.date_validation = timezone.now()
        livraison.statut = Livraison.STATUT_LIVREE
        livraison.save(update_fields=['est_validee', 'methode_validation', 'date_validation', 'statut', 'updated_at'])

        # Mise à jour synchronisée de la commande et des sous-commandes
        commande = livraison.commande
        commande.statut = Commande.STATUT_LIVREE
        commande.save(update_fields=['statut', 'date_modification'])
        commande.sous_commandes.update(statut=Commande.STATUT_LIVREE)

        return livraison
