from rest_framework import permissions
from apps.users.models import Role, ProfilLivreur


class IsLivreurValide(permissions.BasePermission):
    """
    Permission exigée pour effectuer les opérations métier d'un livreur :
    - Utilisateur authentifié ;
    - Possède le rôle LIVREUR ;
    - Possède un ProfilLivreur rattaché ;
    - statut_verification == 'VALIDE'.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False

        # Vérifier si l'utilisateur possède le rôle LIVREUR
        has_role = request.user.roles_attribues.filter(role__nom=Role.LIVREUR).exists()
        if not has_role:
            return False

        # Vérifier si le profil livreur existe et est validé par l'administrateur
        if not hasattr(request.user, 'profil_livreur') or request.user.profil_livreur is None:
            return False

        profil = request.user.profil_livreur
        return profil.statut_verification == ProfilLivreur.STATUT_VALIDE
