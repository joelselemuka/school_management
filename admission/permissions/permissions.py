from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from common.role_services import RoleService



class CanManageAdmission(BasePermission):
    """
    Admin ou personnel admission / secretaire
    """

    def has_permission(self, request, view):

        user = request.user
        
        if not user:
            return PermissionDenied("Utilisateur non connecté")

        return (

            RoleService.is_admin(user)

            or RoleService.is_drh(user)

            or RoleService.is_secretaire(user)

        )


class CanCreateBureauInscription(BasePermission):

    def has_permission(self, request, view):

        user = request.user
        
        if not user:
            return PermissionDenied("utilisateur non connecté")

        return (

            RoleService.is_admin(user)

            or RoleService.is_secretaire(user)

        )
