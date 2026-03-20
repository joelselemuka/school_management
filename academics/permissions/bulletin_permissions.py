from rest_framework.permissions import BasePermission, SAFE_METHODS
from common.role_services import RoleService
from academics.services.acces_service import AccessService


class BulletinPermission(BasePermission):
    """
    Permission pour les Bulletins :
    - Lecture : Admin, Enseignant (ses classes), Élève (son bulletin), Parent (bulletins enfants)
    - Génération (POST via action 'generate') : Admin uniquement (via BulletinService)
    - Modification/Suppression : Admin uniquement
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        # Seul l'admin peut générer / modifier / supprimer des bulletins
        return RoleService.is_admin(request.user)

    def has_object_permission(self, request, view, obj):
        user = request.user

        if RoleService.is_admin(user):
            return True

        # Lecture seule pour les autres rôles
        if request.method not in SAFE_METHODS:
            return False

        if RoleService.is_teacher(user):
            return obj.eleve.inscriptions.filter(
                classe__cours__affectations__enseignant=user.personnel_profile
            ).exists()

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return False
            return obj.eleve_id in eligible_ids

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return False
            return obj.eleve_id in eligible_ids

        return False
