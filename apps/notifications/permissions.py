from rest_framework import permissions


class IsNotificationOwner(permissions.BasePermission):
    """
    Permission DRF garantissant qu'un utilisateur ne peut accéder ou modifier que ses propres notifications.
    """

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return bool(
            request.user and
            request.user.is_authenticated and
            obj.utilisateur == request.user
        )
