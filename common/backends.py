from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from users.models import User


class MultiFieldAuthBackend(ModelBackend):

    def authenticate(self, request, username=None, password=None, **kwargs):

        if username is None or password is None:

            return None


        username = username.strip()


        user = (
            User.objects
            .with_profiles()
            .filter(
                Q(username=username)
                | Q(email__iexact=username, email__isnull=False)
                | Q(matricule=username, matricule__isnull=False)
            )
            .first()
        )


        if user is None:

            User().set_password(password)

            return None


        if not user.is_active:

            return None


        if not user.check_password(password):

            return None


        return user


    def get_user(self, user_id):

        try:

            return User.objects.with_profiles().get(pk=user_id)

        except User.DoesNotExist:

            return None