from rest_framework.permissions import BasePermission, SAFE_METHODS
from common.role_services import RoleService
from academics.services.acces_service import AccessService


class CoursPermission(BasePermission):
    """
    Permission pour les Cours :
    - Lecture : tous les utilisateurs authentifiés
    - Création/Modification/Suppression : Admin uniquement
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return RoleService.is_admin(request.user)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if RoleService.is_admin(user):
            return True

        if RoleService.is_teacher(user):
            return obj.affectations.filter(
                enseignant=user.personnel_profile
            ).exists()

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return False
            return obj.classe.inscriptions.filter(
                eleve_id__in=eligible_ids,
                annee_academique__active=True
            ).exists()

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return False
            return obj.classe.inscriptions.filter(
                eleve_id__in=eligible_ids,
                annee_academique__active=True
            ).exists()

        return False
