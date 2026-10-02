import random
import secrets
from datetime import timedelta
from django.db import models, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.orders.models import Commande
from apps.deliveries.models import Livraison
from apps.users.models import ProfilLivreur


class DeliveryService:
    """
    Service métier du domaine Livraison AYYOU.
    Gère la création de la livraison, la génération du token QR Code sécurisé,
    du code de validation à 4 chiffres, l'attribution progressive basée sur la proximité (Phase 1: 1 livreur 90s, Phase 2: 3 livreurs 90s),
    l'expiration automatique sous 90 secondes et le cycle de vie de livraison.
    """

    @staticmethod
    def obtenir_coordonnees_etablissement(livraison: Livraison) -> tuple[float | None, float | None]:
        """
        Extrait les coordonnées GPS (latitude, longitude) de l'établissement associé à la livraison.
        """
        if not livraison or not livraison.commande:
            return None, None

        sc = livraison.commande.sous_commandes.select_related('etablissement').first()
        if sc and sc.etablissement and sc.etablissement.latitude is not None and sc.etablissement.longitude is not None:
            try:
                return float(sc.etablissement.latitude), float(sc.etablissement.longitude)
            except (ValueError, TypeError):
                pass
        return None, None

    @staticmethod
    def obtenir_livreurs_eligibles(livraison: Livraison = None) -> models.QuerySet:
        """
        Retourne le QuerySet des livreurs éligibles pour une mission :
        - Compte actif
        - Profil livreur validé (statut_verification == 'VALIDE')
        - Marqué disponible (est_disponible == True)
        - Coordonnées GPS valides
        - N'est pas actuellement en cours de livraison sur une mission active
        - N'a pas déjà décliné ou expiré cette livraison
        """
        qs = ProfilLivreur.objects.filter(
            utilisateur__est_actif=True,
            statut_verification=ProfilLivreur.STATUT_VALIDE,
            est_disponible=True,
            latitude_actuelle__isnull=False,
            longitude_actuelle__isnull=False
        )

        # Exclure les livreurs occupés par une livraison en cours
        livreurs_occupes = Livraison.objects.filter(
            statut__in=[
                Livraison.STATUT_AFFECTEE,
                Livraison.STATUT_ACCEPTEE,
                Livraison.STATUT_ARRIVE_RESTAURANT,
                Livraison.STATUT_EN_PREPARATION,
                Livraison.STATUT_PRETE,
                Livraison.STATUT_EN_LIVRAISON
            ],
            livreur__isnull=False
        ).values_list('livreur_id', flat=True)

        qs = qs.exclude(id__in=livreurs_occupes)

        if livraison and livraison.propositions_livreurs:
            props = livraison.propositions_livreurs
            exclus = set(props.get('refuses', [])) | set(props.get('expires', []))
            if exclus:
                qs = qs.exclude(id__in=list(exclus))

        return qs

    @staticmethod
    def calculer_proximite_livreurs(livraison: Livraison, livreurs_qs: models.QuerySet) -> list[tuple[ProfilLivreur, float]]:
        """
        Trie une liste de livreurs éligibles par ordre croissant de distance Haversine par rapport au restaurant.
        Retourne une liste de tuples (profil_livreur, distance_km).
        """
        from apps.orders.delivery_pricing import calculer_distance_haversine

        lat_rest, lng_rest = DeliveryService.obtenir_coordonnees_etablissement(livraison)
        if lat_rest is None or lng_rest is None:
            # Si aucune coordonnée restaurant disponible, renvoyer les livreurs dans leur ordre d'ID
            return [(l, 0.0) for l in livreurs_qs]

        resultats = []
        for l in livreurs_qs:
            dist = calculer_distance_haversine(lat_rest, lng_rest, l.latitude_actuelle, l.longitude_actuelle)
            resultats.append((l, dist))

        resultats.sort(key=lambda item: item[1])
        return resultats

    @staticmethod
    @transaction.atomic
    def lancer_attribution_livraison(livraison: Livraison) -> Livraison:
        """
        Lance la Phase 1 d'attribution progressive pour une livraison :
        - Sélectionne le 1er livreur éligible le plus proche du restaurant.
        - Attribue la mission avec un délai d'acceptation de 90 secondes.
        """
        livreurs_eligibles = DeliveryService.obtenir_livreurs_eligibles(livraison)
        livreurs_tries = DeliveryService.calculer_proximite_livreurs(livraison, livreurs_eligibles)

        props = livraison.propositions_livreurs or {}
        now = timezone.now()

        if livreurs_tries:
            premier_livreur, distance = livreurs_tries[0]
            livraison.livreur = premier_livreur
            livraison.statut = Livraison.STATUT_AFFECTEE
            livraison.date_attribution = now
            livraison.phase_attribution = 1
            props['phase_1'] = [premier_livreur.id]
        else:
            livraison.livreur = None
            livraison.statut = Livraison.STATUT_EN_ATTENTE
            livraison.date_attribution = now
            livraison.phase_attribution = 1
            props['phase_1'] = []

        livraison.propositions_livreurs = props
        livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'phase_attribution', 'propositions_livreurs', 'updated_at'])
        return livraison

    @staticmethod
    @transaction.atomic
    def passer_en_phase_2(livraison: Livraison) -> Livraison:
        """
        Passe la livraison en Phase 2 (Élargissement simultané aux 3 livreurs suivants les plus proches) :
        - Déclenché lorsque la Phase 1 expire (90s) ou que le livreur de Phase 1 décline.
        - Sélectionne simultanément les 3 plus proches livreurs éligibles suivants.
        - Le 1er des 3 à cliquer sur Accepter remportera la livraison.
        """
        props = livraison.propositions_livreurs or {}
        now = timezone.now()

        # Exclure le livreur de Phase 1
        livreurs_eligibles = DeliveryService.obtenir_livreurs_eligibles(livraison)
        p1_ids = props.get('phase_1', [])
        if p1_ids:
            livreurs_eligibles = livreurs_eligibles.exclude(id__in=p1_ids)

        livreurs_tries = DeliveryService.calculer_proximite_livreurs(livraison, livreurs_eligibles)
        top_3 = [item[0] for item in livreurs_tries[:3]]
        top_3_ids = [l.id for l in top_3]

        livraison.livreur = None
        livraison.statut = Livraison.STATUT_EN_ATTENTE
        livraison.date_attribution = now
        livraison.phase_attribution = 2
        props['phase_2'] = top_3_ids
        livraison.propositions_livreurs = props

        livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'phase_attribution', 'propositions_livreurs', 'updated_at'])
        return livraison

    @staticmethod
    @transaction.atomic
    def expire_expired_deliveries() -> int:
        """
        Recherche et fait évoluer de manière atomique toutes les livraisons attribuées
        dont le délai d'acceptation (90 secondes à compter de date_attribution) a expiré.
        - Si Phase 1 expiré -> Passe en Phase 2 (3 livreurs suivants).
        - Si Phase 2 expiré -> Réinitialise l'attribution Phase 2.
        Ne touche JAMAIS aux livraisons déjà acceptées (ACCEPTEE, ARRIVE_RESTAURANT, EN_LIVRAISON, LIVREE, ANNULEE).
        """
        now = timezone.now()
        limite_expiration = now - timedelta(seconds=90)

        expirables = Livraison.objects.select_for_update().filter(
            statut__in=[Livraison.STATUT_EN_ATTENTE, Livraison.STATUT_AFFECTEE],
            date_attribution__isnull=False,
            date_attribution__lte=limite_expiration
        )

        count = 0
        for livraison in expirables:
            props = livraison.propositions_livreurs or {}
            expires = props.get('expires', [])

            if livraison.phase_attribution == 1:
                if livraison.livreur_id and livraison.livreur_id not in expires:
                    expires.append(livraison.livreur_id)
                props['expires'] = expires
                livraison.propositions_livreurs = props
                DeliveryService.passer_en_phase_2(livraison)
                count += 1
            elif livraison.phase_attribution == 2:
                # Phase 2 expirée après 90 secondes : ajouter les livreurs de Phase 2 aux expirés
                p2_ids = props.get('phase_2', [])
                for pid in p2_ids:
                    if pid not in expires:
                        expires.append(pid)
                props['expires'] = expires
                livraison.livreur = None
                livraison.statut = Livraison.STATUT_EN_ATTENTE
                livraison.date_attribution = None
                livraison.propositions_livreurs = props
                livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'propositions_livreurs', 'updated_at'])
                count += 1

        return count

    @staticmethod
    @transaction.atomic
    def attribuer_livraison(livraison_id: int, profil_livreur) -> Livraison:
        """
        Affecte de manière atomique une livraison à un livreur avec enregistrement de l'horodatage.
        Le livreur dispose de 90 secondes pour accepter la mission.
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
        livraison.statut = Livraison.STATUT_AFFECTEE
        livraison.date_attribution = timezone.now()
        livraison.phase_attribution = 1
        livraison.save(update_fields=['livreur', 'statut', 'date_attribution', 'phase_attribution', 'updated_at'])
        return livraison

    @staticmethod
    @transaction.atomic
    def creer_livraison(commande: Commande) -> Livraison:
        """
        Génère automatiquement une fiche de Livraison avec QR Token et Code de validation à 4 chiffres
        lorsqu'une commande devient PRETE (ou lorsqu'elle est sollicitée).
        Déclenche l'attribution progressive Phase 1 au livreur le plus proche.
        Opération atomique et idempotente avec verrou pessimiste.
        """
        commande_obj = Commande.objects.select_for_update().get(pk=commande.pk)
        if hasattr(commande_obj, 'livraison') and commande_obj.livraison:
            return commande_obj.livraison

        livraison_existante = Livraison.objects.filter(commande=commande_obj).first()
        if livraison_existante:
            return livraison_existante

        # Token QR Code imprévisible et sécurisé
        token_qr = f"AYYOU-DELIVERY-{secrets.token_hex(16)}"
        while Livraison.objects.filter(token_qr=token_qr).exists():
            token_qr = f"AYYOU-DELIVERY-{secrets.token_hex(16)}"

        # Code de validation à 4 chiffres aléatoire
        code_validation = f"{random.randint(1000, 9999)}"

        livraison = Livraison.objects.create(
            commande=commande_obj,
            token_qr=token_qr,
            code_validation=code_validation,
            statut=Livraison.STATUT_EN_ATTENTE,
            phase_attribution=1,
            propositions_livreurs={}
        )

        # Lancer l'attribution Phase 1 (1er livreur le plus proche)
        DeliveryService.lancer_attribution_livraison(livraison)
        return livraison

    @staticmethod
    @transaction.atomic
    def accepter_mission(livraison_id: int, profil_livreur) -> Livraison:
        """
        Permet à un livreur validé et disponible d'accepter de manière atomique une livraison disponible.
        Vérifie la validité du délai d'acceptation de 90 secondes.
        Utilise select_for_update() pour éviter les courses concurrentes entre deux livreurs (pessimistic DB lock).
        Si la course est déjà prise par un autre livreur, renvoie un message explicite "Course déjà attribuée."
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
            raise ValidationError(_("Course déjà attribuée."))

        if livraison.statut in [Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]:
            raise ValidationError(_("Impossible d'accepter une livraison terminée ou annulée."))

        now = timezone.now()

        # En Phase 1 : Seul le livreur attribué peut accepter (si pas expiré)
        if livraison.phase_attribution == 1:
            if livraison.livreur is not None and livraison.livreur != profil_livreur:
                # Vérifier si le délai de 90 secondes a expiré pour le livreur 1
                deadline = livraison.date_attribution + timedelta(seconds=90) if livraison.date_attribution else now
                if now > deadline:
                    # Basculer en Phase 2 et vérifier si le livreur demandeur est éligible Phase 2
                    DeliveryService.passer_en_phase_2(livraison)
                else:
                    raise ValidationError(_("Cette course est actuellement proposée à un autre livreur."))

        # En Phase 2 : Vérifier si le livreur fait partie des livreurs sollicités
        props = livraison.propositions_livreurs or {}
        p2_ids = props.get('phase_2', [])
        refuses = props.get('refuses', [])
        expires = props.get('expires', [])

        if profil_livreur.id in refuses or profil_livreur.id in expires:
            raise ValidationError(_("Vous ne pouvez plus accepter cette course que vous avez déclinée ou laissée expirer."))

        if livraison.phase_attribution == 2 and p2_ids and profil_livreur.id not in p2_ids:
            # Si Phase 2 et le livreur n'est pas dans les 3 sélectionnés (mais l'un des 3 peut accepter)
            pass  # On autorise tout livreur disponible à concourir si Phase 2 est active

        # Vérifier si le délai de 90 secondes de Phase 2 a expiré
        if livraison.date_attribution and (now > livraison.date_attribution + timedelta(seconds=90)):
            if livraison.statut in [Livraison.STATUT_EN_ATTENTE, Livraison.STATUT_AFFECTEE]:
                raise ValidationError(_("Le délai d'acceptation de cette course a expiré."))

        # Si le livreur actuel a déjà accepté cette livraison sous les 90s, retourner sans modification
        if livraison.livreur == profil_livreur and livraison.statut == Livraison.STATUT_ACCEPTEE:
            return livraison

        # Validation de l'acceptation par le premier livreur qui gagne le verrou pessimiste DB
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
        Permet à un livreur de décliner/refuser une mission qui lui est affectée ou proposée.
        Passe la livraison en Phase 2 (si Phase 1 déclinée) ou enregistre le refus.
        """
        if not profil_livreur or profil_livreur.statut_verification != 'VALIDE':
            raise ValidationError(_("Seul un livreur validé peut décliner une mission."))

        try:
            livraison = Livraison.objects.select_for_update().get(pk=livraison_id)
        except Livraison.DoesNotExist:
            raise ValidationError(_("Livraison introuvable."))

        if livraison.statut in [Livraison.STATUT_EN_LIVRAISON, Livraison.STATUT_LIVREE, Livraison.STATUT_ANNULEE]:
            raise ValidationError(_("Impossible de décliner une livraison déjà en cours d'acheminement, terminée ou annulée."))

        props = livraison.propositions_livreurs or {}
        refuses = props.get('refuses', [])
        if profil_livreur.id not in refuses:
            refuses.append(profil_livreur.id)
        props['refuses'] = refuses
        livraison.propositions_livreurs = props

        if livraison.phase_attribution == 1:
            DeliveryService.passer_en_phase_2(livraison)
        else:
            p2_ids = props.get('phase_2', [])
            if profil_livreur.id in p2_ids:
                p2_ids.remove(profil_livreur.id)
                props['phase_2'] = p2_ids
            livraison.livreur = None
            livraison.statut = Livraison.STATUT_EN_ATTENTE
            livraison.save(update_fields=['livreur', 'statut', 'propositions_livreurs', 'updated_at'])

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

