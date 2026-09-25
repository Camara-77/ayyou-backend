import random
import secrets
from datetime import timedelta
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
    du code de validation à 6 chiffres, l'affectation des missions, l'expiration automatique
    des demandes non acceptées sous 2 minutes et le cycle de vie de livraison.
    """

    @staticmethod
    @transaction.atomic
    def expire_expired_deliveries() -> int:
        """
        Recherche et réinitialise de manière atomique toutes les livraisons attribuées
        dont le délai d'acceptation (2 minutes à compter de date_attribution) a expiré.
        Ces livraisons sont remises en attente (livreur=None, date_attribution=None, statut=EN_ATTENTE).
        Ne touche JAMAIS aux livraisons déjà acceptées (ACCEPTEE, ARRIVE_RESTAURANT, EN_LIVRAISON, LIVREE, ANNULEE).
        """
        now = timezone.now()
        limite_expiration = now - timedelta(minutes=2)

        expirables = Livraison.objects.select_for_update().filter(
            livreur__isnull=False,
            statut__in=[Livraison.STATUT_EN_ATTENTE, Livraison.STATUT_AFFECTEE],
            date_attribution__lte=limite_expiration
        )

        count = 0
        for livraison in expirables:
            livraison.livreur = None
            livraison.statut = Livraison.STATUT_EN_ATTENTE
            livraison.date_attribution = None
            livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'updated_at'])
            count += 1

        return count

    @staticmethod
    @transaction.atomic
    def attribuer_livraison(livraison_id: int, profil_livreur) -> Livraison:
        """
        Affecte de manière atomique une livraison à un livreur avec enregistrement de l'horodatage.
        Le livreur dispose de 2 minutes pour accepter la mission.
        """
        if not profil_livreur or profil_livreur.statut_verification != 'VALIDE':
            raise ValidationError(_("Seul un livreur validé peut recevoir une mission."))

        try:
            livraison = Livraison.objects.select_for_update().get(pk=livraison_id)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Livraison introuvable."))

        if livraison.statut in [
            Livraison.STATUT_ACCEPTEE,
            Livraison.STATUT_ARRIVE_RESTAURANT,
            Livraison.STATUT_EN_PREPARATION,
            Livraison.STATUT_PRETE,
            Livraison.STATUT_EN_LIVRAISON,
            Livraison.STATUT_LIVREE,
            Livraison.STATUT_ANNULEE
        ] and livraison.livreur is not None:
            raise ValidationError(_("Impossible d'attribuer une livraison déjà acceptée ou terminée."))

        livraison.livreur = profil_livreur
        livraison.statut = Livraison.STATUT_EN_ATTENTE
        livraison.date_attribution = timezone.now()
        livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'updated_at'])
        return livraison

    @staticmethod
    @transaction.atomic
    def creer_livraison(commande: Commande) -> Livraison:
        """
        Génère automatiquement une fiche de Livraison avec QR Token et Code de validation à 6 chiffres
        lorsqu'une commande devient PRETE (ou lorsqu'elle est sollicitée).
        Opération atomique et idempotente avec verrou pessimiste.
        """
        commande_obj = Commande.objects.select_for_update().get(pk=commande.pk)
        if hasattr(commande_obj, 'livraison') and commande_obj.livraison:
            return commande_obj.livraison

        livraison_existante = Livraison.objects.filter(commande=commande_obj).first()
        if livraison_existante:
            return livraison_existante

        # Token QR Code imprévisible et sécurisé (ne contient aucune donnée personnelle sensible)
        token_qr = f"AYYOU-DELIVERY-{secrets.token_hex(16)}"
        while Livraison.objects.filter(token_qr=token_qr).exists():
            token_qr = f"AYYOU-DELIVERY-{secrets.token_hex(16)}"

        # Code de validation à 4 chiffres aléatoire
        code_validation = f"{random.randint(1000, 9999)}"

        livraison = Livraison.objects.create(
            commande=commande_obj,
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
        Vérifie la validité du délai d'acceptation de 2 minutes.
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

        # Vérifier si la mission a déjà été acceptée par UN AUTRE livreur
        if livraison.statut in [
            Livraison.STATUT_ACCEPTEE,
            Livraison.STATUT_ARRIVE_RESTAURANT,
            Livraison.STATUT_EN_LIVRAISON
        ] and livraison.livreur is not None and livraison.livreur != profil_livreur:
            raise ValidationError(_("Cette mission a déjà été acceptée par un autre livreur."))

        if livraison.statut in [Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]:
            raise ValidationError(_("Impossible d'accepter une livraison terminée ou annulée."))

        now = timezone.now()

        # Vérifier si la course était attribuée et si le délai de 2 minutes a expiré
        if livraison.livreur is not None and livraison.date_attribution is not None and livraison.statut in [Livraison.STATUT_EN_ATTENTE, Livraison.STATUT_AFFECTEE]:
            deadline = livraison.date_attribution + timedelta(minutes=2)
            if now > deadline:
                est_meme_livreur = (livraison.livreur == profil_livreur)

                # Expiration automatique et libération immédiate
                livraison.livreur = None
                livraison.statut = Livraison.STATUT_EN_ATTENTE
                livraison.date_attribution = None
                livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'updated_at'])

                if est_meme_livreur:
                    raise ValidationError(_("Le délai d'acceptation de cette course est expiré."))

        # Si le livreur actuel a déjà accepté cette livraison sous les 2 min, retourner sans modification
        if livraison.livreur == profil_livreur and livraison.statut == Livraison.STATUT_ACCEPTEE:
            return livraison

        # Validation de l'acceptation
        livraison.livreur = profil_livreur
        livraison.statut = Livraison.STATUT_ACCEPTEE
        livraison.date_attribution = now
        livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'updated_at'])

        # Mise à jour synchronisée de la date de modification de la commande
        commande = livraison.commande
        if commande:
            commande.save(update_fields=['date_modification'])

        return livraison

    @staticmethod
    @transaction.atomic
    def refuser_mission(livraison_id: int, profil_livreur) -> Livraison:
        """
        Permet à un livreur de décliner/refuser une mission qui lui est affectée.
        Libère la course afin qu'elle redevienne disponible pour d'autres livreurs.
        Ne supprime pas la commande ni la livraison.
        """
        if not profil_livreur or profil_livreur.statut_verification != 'VALIDE':
            raise ValidationError(_("Seul un livreur validé peut décliner une mission."))

        try:
            livraison = Livraison.objects.select_for_update().get(pk=livraison_id)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Livraison introuvable."))

        if livraison.livreur != profil_livreur:
            raise ValidationError(_("Cette livraison n'est pas attribuée à votre compte."))

        if livraison.statut in [Livraison.STATUT_EN_LIVRAISON, Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]:
            raise ValidationError(_("Impossible de décliner une livraison déjà en cours d'acheminement, terminée ou annulée."))

        livraison.livreur = None
        livraison.statut = Livraison.STATUT_EN_ATTENTE
        livraison.date_attribution = None
        livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'updated_at'])

        return livraison

    @staticmethod
    @transaction.atomic
    def arriver_restaurant(livraison_id: int, profil_livreur) -> Livraison:
        """
        Déclare l'arrivée du livreur au restaurant/vendeur.
        Passe la livraison à l'état ARRIVE_RESTAURANT.
        """
        if not profil_livreur or profil_livreur.statut_verification != 'VALIDE':
            raise ValidationError(_("Seul un livreur validé peut effectuer cette action."))

        try:
            livraison = Livraison.objects.select_for_update().get(pk=livraison_id)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Livraison introuvable."))

        if livraison.livreur != profil_livreur:
            raise ValidationError(_("Cette livraison n'est pas affectée à votre compte."))

        if livraison.statut in [Livraison.STATUT_EN_LIVRAISON, Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]:
            raise ValidationError(_("Impossible de déclarer l'arrivée pour une livraison terminée ou annulée."))

        livraison.statut = Livraison.STATUT_ARRIVE_RESTAURANT
        livraison.save(update_fields=['statut', 'updated_at'])

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

        code_req = code_validation.strip()
        if len(code_req) != 4 or not code_req.isdigit():
            raise ValidationError(_("Le code de validation doit comporter exactement 4 chiffres."))

        code_stored = livraison.code_validation.strip()
        if code_stored != code_req:
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

    @staticmethod
    @transaction.atomic
    def synchroniser_statuts_apres_sous_commande(sous_commande) -> Commande:
        """
        Recalcule et synchronise les statuts de la Commande principale et de la Livraison associée
        suite au changement de statut d'une SousCommande marchand.
        Gère les cas multi-établissements (ex: 2 sous-commandes).
        """
        commande = sous_commande.commande
        toutes_sc = list(commande.sous_commandes.all())
        if not toutes_sc:
            return commande

        sc_actives = [sc for sc in toutes_sc if sc.statut != Commande.STATUT_ANNULEE]

        if not sc_actives:
            nouveau_statut_cmd = Commande.STATUT_ANNULEE
            nouveau_statut_livr = Livraison.STATUT_ANNULEE
        elif all(sc.statut == Commande.STATUT_PRETE for sc in sc_actives):
            nouveau_statut_cmd = Commande.STATUT_PRETE
            nouveau_statut_livr = Livraison.STATUT_PRETE
        elif any(sc.statut in [Commande.STATUT_EN_PREPARATION, Commande.STATUT_PRETE] for sc in sc_actives):
            nouveau_statut_cmd = Commande.STATUT_EN_PREPARATION
            nouveau_statut_livr = Livraison.STATUT_EN_PREPARATION
        else:
            nouveau_statut_cmd = commande.statut
            nouveau_statut_livr = None

        # Mise à jour de la Commande principale
        if commande.statut != nouveau_statut_cmd:
            commande.statut = nouveau_statut_cmd
            commande.save(update_fields=['statut', 'date_modification'])

        # Si la commande est PRETE, créer la livraison si elle n'existe pas encore
        if nouveau_statut_cmd == Commande.STATUT_PRETE:
            if not hasattr(commande, 'livraison') or not commande.livraison:
                DeliveryService.creer_livraison(commande)
                try:
                    commande.refresh_from_db()
                except Exception:
                    pass

        # Mise à jour de la Livraison associée si elle existe
        if hasattr(commande, 'livraison') and commande.livraison:
            livraison = commande.livraison
            if nouveau_statut_livr:
                statuts_irreversibles = [Livraison.STATUT_EN_LIVRAISON, Livraison.STATUT_LIVREE]
                if livraison.statut not in statuts_irreversibles or nouveau_statut_livr == Livraison.STATUT_ANNULEE:
                    if livraison.statut != nouveau_statut_livr:
                        livraison.statut = nouveau_statut_livr
                        livraison.save(update_fields=['statut', 'updated_at'])

        return commande

    @staticmethod
    def obtenir_statistiques_livreur(profil_livreur) -> dict:
        """
        Calcule les statistiques réelles BDD de la journée pour un livreur donné.
        """
        if not profil_livreur:
            return {'courses_terminees': 0, 'gain_total': '0', 'distance_km': None, 'temps_connecte': None}

        aujourdhui = timezone.now().date()
        livraisons_livrees = Livraison.objects.filter(
            livreur=profil_livreur,
            statut=Livraison.STATUT_LIVREE,
            date_validation__date=aujourdhui
        ).select_related('commande')

        count = livraisons_livrees.count()
        gain = 0
        for liv in livraisons_livrees:
            if liv.commande and liv.commande.frais_livraison:
                gain += int(liv.commande.frais_livraison)

        return {
            'courses_terminees': count,
            'gain_total': f"{gain:,}".replace(',', ' '),
            'distance_km': None,
            'temps_connecte': None
        }

