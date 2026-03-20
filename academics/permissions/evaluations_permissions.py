from rest_framework.permissions import BasePermission, SAFE_METHODS
from common.role_services import RoleService
from academics.services.acces_service import AccessService


class EvaluationPermission(BasePermission):
    """
    Permission pour les Évaluations :
    - Lecture : tous les utilisateurs authentifiés
    - Création (POST) : Enseignant (sur ses cours) ou Admin
    - Modification/Suppression : Admin uniquement
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        if request.method == "POST":
            user = request.user

            # Admin peut toujours créer
            if RoleService.is_admin(user):
                return True

            # Enseignant : vérifie qu'il est affecté au cours
            if RoleService.is_teacher(user):
                cours_id = request.data.get("cours")
                if not cours_id:
                    return False
                return user.personnel_profile.affectations.filter(
                    cours_id=cours_id
                ).exists()

            return False

        return RoleService.is_admin(request.user)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if RoleService.is_admin(user):
            return True

        if RoleService.is_teacher(user):
            return obj.cours.affectations.filter(
                enseignant=user.personnel_profile
            ).exists()

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return False
            return obj.cours.classe.inscriptions.filter(
                eleve_id__in=eligible_ids
            ).exists()

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return False
            return obj.cours.classe.inscriptions.filter(
                eleve_id__in=eligible_ids
            ).exists()

        return False
