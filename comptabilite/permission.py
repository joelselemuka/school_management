from rest_framework.permissions import BasePermission
from rest_framework.permissions import BasePermission, SAFE_METHODS

class ComptabilitePermission(BasePermission):

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        if user.is_superuser:
            return True

        if hasattr(user, "personnel_profile"):
            if user.personnel_profile.fonction in ["comptable", "admin"]:
                return True

        if request.method in SAFE_METHODS:
            return True

        return False
    
    
    
class IsAdminOrAccountant(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_admin or request.user.is_comptable
        )

