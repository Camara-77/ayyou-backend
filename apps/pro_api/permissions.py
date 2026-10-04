from rest_framework import permissions
from apps.users.models import Role


class IsApprovedMerchant(permissions.BasePermission):
    """
    Permission DRF exigeant :
    1. Utilisateur authentifié et actif (est_actif=True).
    2. Rôle RESTAURANT ou VENDEUR.
    3. Au moins un Établissement (statut VALIDE ou essai/abonnement ACTIF non expiré).
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.est_actif):
            return False

        has_merchant_role = request.user.roles_attribues.filter(
            role__nom__in=[Role.RESTAURANT, Role.VENDEUR]
        ).exists()
        if not has_merchant_role:
            return False

        from apps.catalog.models import Etablissement
        from django.utils import timezone
        from django.db.models import Q
        now = timezone.now()

        return request.user.etablissements.filter(
            Q(statut_verification=Etablissement.STATUT_VALIDE) |
            (Q(statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF) & Q(date_expiration_abonnement__gt=now))
        ).exists()


class IsApprovedRestaurant(permissions.BasePermission):
    """
    Permission DRF exigeant :
    1. Utilisateur authentifié et actif.
    2. Rôle RESTAURANT.
    3. Établissement de type RESTAURANT (VALIDE ou abonnement/essai ACTIF non expiré).
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.est_actif):
            return False

        has_role = request.user.roles_attribues.filter(role__nom=Role.RESTAURANT).exists()
        if not has_role:
            return False

        from apps.catalog.models import Etablissement
        from django.utils import timezone
        from django.db.models import Q
        now = timezone.now()

        return request.user.etablissements.filter(
            Q(type_etablissement=Etablissement.TYPE_RESTAURANT) &
            (Q(statut_verification=Etablissement.STATUT_VALIDE) |
             (Q(statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF) & Q(date_expiration_abonnement__gt=now)))
        ).exists()


class IsApprovedVendeur(permissions.BasePermission):
    """
    Permission DRF exigeant :
    1. Utilisateur authentifié et actif.
    2. Rôle VENDEUR.
    3. Établissement de type VENDEUR (VALIDE ou abonnement/essai ACTIF non expiré).
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.est_actif):
            return False

        has_role = request.user.roles_attribues.filter(role__nom=Role.VENDEUR).exists()
        if not has_role:
            return False

        from apps.catalog.models import Etablissement
        from django.utils import timezone
        from django.db.models import Q
        now = timezone.now()

        return request.user.etablissements.filter(
            Q(type_etablissement=Etablissement.TYPE_VENDEUR) &
            (Q(statut_verification=Etablissement.STATUT_VALIDE) |
             (Q(statut_abonnement=Etablissement.STATUT_ABONNEMENT_ACTIF) & Q(date_expiration_abonnement__gt=now)))
        ).exists()


class IsApprovedDriver(permissions.BasePermission):
    """
    Permission DRF exigeant :
    1. Utilisateur authentifié et actif (est_actif=True).
    2. Rôle LIVREUR.
    3. ProfilLivreur avec statut_verification='VALIDE'.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.est_actif):
            return False

        has_driver_role = request.user.roles_attribues.filter(
            role__nom=Role.LIVREUR
        ).exists()
        if not has_driver_role:
            return False

        return (
            hasattr(request.user, 'profil_livreur') and
            request.user.profil_livreur is not None and
            request.user.profil_livreur.statut_verification == 'VALIDE'
        )


class IsApprovedPro(permissions.BasePermission):
    """
    Permission DRF générique exigeant que l'utilisateur soit un professionnel approuvé
    (soit Marchand approuvé, soit Livreur approuvé).
    """
    def has_permission(self, request, view):
        merchant_perm = IsApprovedMerchant()
        driver_perm = IsApprovedDriver()
        return merchant_perm.has_permission(request, view) or driver_perm.has_permission(request, view)


class IsProCandidate(permissions.BasePermission):
    """
    Permission autorisant l'accès aux utilisateurs connectés possédant un rôle PRO
    (RESTAURANT, VENDEUR, LIVREUR), quel que soit le statut de leur candidature (EN_ATTENTE, VALIDE, REFUSE).
    Utilisé exclusivement pour consulter l'état du dossier.
    """
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.est_actif):
            return False
        return request.user.roles_attribues.filter(
            role__nom__in=[Role.RESTAURANT, Role.VENDEUR, Role.LIVREUR]
        ).exists()
