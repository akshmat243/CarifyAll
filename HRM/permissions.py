# accounts/permissions.py
from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    """
    Allow only admin role OR superuser to perform write actions.
    """
    def has_permission(self, request, view):
        # Allow read-only requests for all authenticated users
        if request.method in permissions.SAFE_METHODS:
            return True

        # Superuser bypasses all restrictions
        if request.user.is_superuser:
            return True

        # Only admin role can modify data
        return request.user.role == "admin"