from django.contrib.auth import get_user_model

User = get_user_model()


class RoleService:
    """
    Service professionnel de gestion des rôles et fonctions.
    """

    # =====================
    # PROPRIÉTÉS SYSTEME
    # =====================

    @staticmethod
    def is_authenticated(user):

        return user and user.is_authenticated


    @staticmethod
    def is_admin(user):

        return user.is_superuser


    @staticmethod
    def is_staff(user):

        return user.is_staff


    # =====================
    # ROLES METIER
    # =====================

    @staticmethod
    def is_student(user):

        return getattr(user, "is_student", False)


    @staticmethod
    def is_parent(user):

        return getattr(user, "is_parent", False)


    @staticmethod
    def is_personnel(user):

        return getattr(user, "is_personnel", False)


    # =====================
    # FONCTION PERSONNEL
    # =====================

    @staticmethod
    def get_personnel_function(user):

        if not RoleService.is_personnel(user):

            return None

        return user.personnel_profile.fonction


    @staticmethod
    def is_teacher(user):

        return (
            RoleService.is_personnel(user)
            and user.personnel_profile.fonction == "enseignant"
        )


    @staticmethod
    def is_accountant(user):

        return (
            RoleService.is_personnel(user)
            and user.personnel_profile.fonction == "comptable"
        )


    @staticmethod
    def is_secretary(user):

        return (
            RoleService.is_personnel(user)
            and user.personnel_profile.fonction == "secretaire"
        )


    @staticmethod
    def is_librarian(user):

        return (
            RoleService.is_personnel(user)
            and user.personnel_profile.fonction == "bibliothecaire"
        )


    @staticmethod
    def is_transport_manager(user):

        return (
            RoleService.is_personnel(user)
            and user.personnel_profile.fonction == "responsable_transport"
        )


    @staticmethod
    def is_driver(user):

        return (
            RoleService.is_personnel(user)
            and user.personnel_profile.fonction == "chauffeur"
        )


    # =====================
    # MULTI ROLE
    # =====================

    @staticmethod
    def get_roles(user):

        roles = []

        if RoleService.is_student(user):

            roles.append("student")

        if RoleService.is_parent(user):

            roles.append("parent")

        if RoleService.is_personnel(user):

            roles.append("personnel")

        if RoleService.is_admin(user):

            roles.append("admin")

        return roles
    
  