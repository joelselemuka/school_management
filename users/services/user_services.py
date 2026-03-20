from common.role_services import User

from ..models import ParentEleve, Parent

from django.db import transaction
from django.contrib.auth import get_user_model
import secrets

password = secrets.token_urlsafe(10)
User = get_user_model()


class UserService:


    @staticmethod
    @transaction.atomic
    def create_user(

        username,

        matricule,


        email=None,

        is_staff=False

    ):


        password = secrets.token_urlsafe(10)


        user = User.objects.create_user(

            username=username,

            matricule=matricule,

            email=email,

            password=password,

            is_staff=is_staff
            

        )


        return user


    @staticmethod
    def get_with_profiles(user_id):

        return (

            User.objects

            .with_profiles()

            .get(id=user_id)

        )


    @staticmethod
    def is_parent_of(user, eleve):

        if not user.is_parent:

            return False


        return (

            user.parent_profile.enfants

            .filter(id=eleve.id)

            .exists()

        )


    @staticmethod
    def get_reduction_for(user, eleve):

        if not user.is_parent:

            return 0


        relation = (

            user.parent_profile.enfants

            .filter(id=eleve.id)

            .first()

        )


        return relation.reduction_percent if relation else 0

    @staticmethod
    def is_parent_of(user, eleve):
        try:
            parent = user.parent
        except Parent.DoesNotExist:
            return False

        return ParentEleve.objects.filter(parent=parent, eleve=eleve).exists()

    @staticmethod
    def get_reduction_for(user, eleve):
        try:
            parent = user.parent
        except Parent.DoesNotExist:
            return 0

        relation = ParentEleve.objects.filter(parent=parent, eleve=eleve).first()

        return relation.reduction_percent if relation else 0

    
    @staticmethod
    def get_current_user(user):

        return (
            User.objects
            .with_profiles()
            .get(id=user.id)
        )