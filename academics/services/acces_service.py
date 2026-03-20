from academics.models import (
    Classe,
    Cours,
    Note,
    Evaluation,
    Bulletin,
    AffectationEnseignant
)
from common.role_services import RoleService
from finance.models import DetteEleve



class AccessService:
    """
    Service de filtrage des querysets selon le rôle de l'utilisateur.
    Garantit le cloisonnement des données : chaque utilisateur ne voit
    que les entités auxquelles il a accès.
    """

    # -------------------
    # CLASSES
    # -------------------

    @staticmethod
    def _eligible_eleve_ids(user):
        """
        Retourne les IDs des élèves autorisés (frais obligatoires payés).
        Pour les rôles non concernés, retourne None.
        """
        from users.models import ParentEleve

        if RoleService.is_student(user):
            eleve = getattr(user, "eleve_profile", None)
            if not eleve:
                return []
            eleve_ids = [eleve.id]
        elif RoleService.is_parent(user):
            eleve_ids = list(
                ParentEleve.objects.filter(parent=user.parent_profile)
                .values_list("eleve_id", flat=True)
            )
        else:
            return None

        if not eleve_ids:
            return []

        blocked_ids = set(
            DetteEleve.objects.filter(
                eleve_id__in=eleve_ids,
                frais__obligatoire=True
            ).exclude(statut="PAYE")
            .values_list("eleve_id", flat=True)
        )

        return [eid for eid in eleve_ids if eid not in blocked_ids]

    @staticmethod
    def get_user_classes(user):

        if RoleService.is_admin(user) or RoleService.is_staff(user):
            return Classe.objects.all()

        if RoleService.is_teacher(user):
            return Classe.objects.filter(
                cours__affectations__enseignant=user.personnel_profile
            ).distinct()

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Classe.objects.none()
            return Classe.objects.filter(
                inscriptions__eleve_id__in=eligible_ids,
                inscriptions__annee_academique__active=True
            )

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Classe.objects.none()
            return Classe.objects.filter(
                inscriptions__eleve_id__in=eligible_ids,
                inscriptions__annee_academique__active=True
            ).distinct()

        return Classe.objects.none()

    # -------------------
    # COURS
    # -------------------

    @staticmethod
    def get_user_courses(user):

        if RoleService.is_admin(user) or RoleService.is_staff(user):
            return Cours.objects.all()

        if RoleService.is_teacher(user):
            return Cours.objects.filter(
                affectations__enseignant=user.personnel_profile
            )

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Cours.objects.none()
            return Cours.objects.filter(
                classe__inscriptions__eleve_id__in=eligible_ids,
                classe__inscriptions__annee_academique__active=True
            )

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Cours.objects.none()
            return Cours.objects.filter(
                classe__inscriptions__eleve_id__in=eligible_ids,
                classe__inscriptions__annee_academique__active=True
            )

        return Cours.objects.none()

    # -------------------
    # NOTES
    # -------------------

    @staticmethod
    def get_user_notes(user):

        if RoleService.is_admin(user) or RoleService.is_staff(user):
            return Note.objects.all()

        if RoleService.is_teacher(user):
            return Note.objects.filter(
                evaluation__cours__affectations__enseignant=user.personnel_profile
            )

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Note.objects.none()
            return Note.objects.filter(
                eleve_id__in=eligible_ids
            )

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Note.objects.none()
            return Note.objects.filter(
                eleve_id__in=eligible_ids
            )

        return Note.objects.none()

    # -------------------
    # EVALUATIONS
    # -------------------

    @staticmethod
    def get_user_evaluations(user):

        if RoleService.is_admin(user) or RoleService.is_staff(user):
            return Evaluation.objects.all()

        if RoleService.is_teacher(user):
            return Evaluation.objects.filter(
                cours__affectations__enseignant=user.personnel_profile
            )

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Evaluation.objects.none()
            return Evaluation.objects.filter(
                cours__classe__inscriptions__eleve_id__in=eligible_ids
            )

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Evaluation.objects.none()
            return Evaluation.objects.filter(
                cours__classe__inscriptions__eleve_id__in=eligible_ids
            )

        return Evaluation.objects.none()

    # -------------------
    # BULLETINS
    # -------------------

    @staticmethod
    def get_user_bulletins(user):

        if RoleService.is_admin(user) or RoleService.is_staff(user):
            return Bulletin.objects.all()

        if RoleService.is_teacher(user):
            return Bulletin.objects.filter(
                eleve__inscriptions__classe__cours__affectations__enseignant=user.personnel_profile
            ).distinct()

        if RoleService.is_student(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Bulletin.objects.none()
            return Bulletin.objects.filter(
                eleve_id__in=eligible_ids
            )

        if RoleService.is_parent(user):
            eligible_ids = AccessService._eligible_eleve_ids(user)
            if not eligible_ids:
                return Bulletin.objects.none()
            return Bulletin.objects.filter(
                eleve_id__in=eligible_ids
            )

        return Bulletin.objects.none()
