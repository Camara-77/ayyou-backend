from rest_framework import permissions
from apps.users.models import Role


class IsSuperAdmin(permissions.BasePermission):
    """
    Permission DRF stricte pour la console Super Admin AYYOU.
    Exige :
    - Utilisateur authentifié via JWT (Header Authorization: Bearer <token>) ;
    - is_staff=True OU is_superuser=True OU rôle ADMINISTRATEUR attribué dans UtilisateurRole.

    Garantit qu'un Client, Livreur, Restaurant ou Vendeur standard est strictement bloqué (HTTP 403 Forbidden).
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Vérifier si is_staff ou is_superuser
        if request.user.is_staff or request.user.is_superuser:
            return True

        # Vérifier l'attribution explicite du rôle ADMINISTRATEUR
        return request.user.roles_attribues.filter(role__nom=Role.ADMINISTRATEUR).exists()
