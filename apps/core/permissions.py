from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    """
    Object-level permission: allows access only if obj.created_by == request.user.
    """

    def has_object_permission(self, request, view, obj):
        return obj.created_by == request.user
