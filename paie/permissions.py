"""
Permissions du module Paie.

CanManagePayroll : accordée aux rôles DRH (personnel.fonction == 'drh'),
                  Administrateur (superuser) et Staff.

RoleService ne fournit pas is_director / is_drh directement.
On regarde la fonction du profil personnel.
"""

from rest_framework.permissions import BasePermission
from common.role_services import RoleService


def _is_drh_or_director(user):
    """Retourne True si l'utilisateur est DRH ou Directeur (fonctions RH)."""
    if not RoleService.is_personnel(user):
        return False
    fonction = getattr(user, "personnel_profile", None)
    if fonction is None:
        return False
    return user.personnel_profile.fonction in ("drh", "admin", "directeur")


class CanManagePayroll(BasePermission):
    """
    Permission de gestion de la paie du personnel.

    Lecture autorisée pour :
      - Administrateur (superuser)
      - Staff Django (is_staff)
      - DRH / Directeur / Admin (fonction du profil personnel)

    Écriture réservée à :
      - Administrateur (superuser)
      - DRH / Directeur / Admin (fonction du profil personnel)
    """

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False

        is_privileged = (
            RoleService.is_admin(user)
            or RoleService.is_staff(user)
            or _is_drh_or_director(user)
        )

        if request.method in ("GET", "HEAD", "OPTIONS"):
            return is_privileged

        # Écriture : superuser ou DRH/directeur/admin
        return RoleService.is_admin(user) or _is_drh_or_director(user)
