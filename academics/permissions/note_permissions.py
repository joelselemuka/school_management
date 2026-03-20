from rest_framework.permissions import BasePermission, SAFE_METHODS

from academics.models import Evaluation
from common.role_services import RoleService
from academics.services.acces_service import AccessService


class NotePermission(BasePermission):
    """
    Permission pour les Notes :
    - Lecture : Admin, Enseignant (ses cours), Élève (ses notes), Parent (notes enfants)
    - Création (POST) : Enseignant uniquement (sur ses cours)
    - Modification (PUT/PATCH) : Admin uniquement (enseignant interdit après création)
    - Suppression (DELETE) : Admin uniquement
    """

    def has_permission(self, request, view):
        user = request.user

        if not user.is_authenticated:
            return False

        # Lecture autorisée pour tous les authentifiés
        if request.method in SAFE_METHODS:
            return True

        # Création : réservée aux enseignants
        if request.method == "POST":
            if not RoleService.is_teacher(user):
                return False

            evaluation_id = request.data.get("evaluation")
            if not evaluation_id:
                return False

            try:
                evaluation = Evaluation.objects.get(id=evaluation_id)
            except Evaluation.DoesNotExist:
                return False

            return evaluation.cours.affectations.filter(
                enseignant=user.personnel_profile
            ).exists()

        # PUT/PATCH/DELETE : admin uniquement
        # Les enseignants ne peuvent PAS modifier une note après création
        return RoleService.is_admin(user)

    def has_object_permission(self, request, view, obj):
        user = request.user

        # Admin : accès total
        if RoleService.is_admin(user):
            return True

        # Lecture seule
        if request.method in SAFE_METHODS:
            if RoleService.is_teacher(user):
                return obj.evaluation.cours.affectations.filter(
                    enseignant=user.personnel_profile
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

        # PUT/PATCH : enseignant INTERDIT (ne peut pas modifier après création)
        if request.method in ['PUT', 'PATCH']:
            if RoleService.is_teacher(user):
                return False

        return False
