from rest_framework.permissions import BasePermission, SAFE_METHODS

from common.role_services import RoleService


class FinancePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        # SUPERADMIN
        if user.is_superuser:
            return True

        # ADMIN : lecture seule finance
        if RoleService.is_admin(user):
            if request.method in SAFE_METHODS:
                return True
            return False

        # COMPTABLE : plein accès paiements
        if RoleService.is_comptable(user):
            return True

        # Parent / Élève : lecture seule
        if request.method in SAFE_METHODS:
            if RoleService.is_parent(user) or RoleService.is_eleve(user):
                return True

        return False
