from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework.exceptions import AuthenticationFailed


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):

    username_field = "login"


    def validate(self, attrs):

        login = attrs.get("login")
        password = attrs.get("password")


        user = authenticate(
            request=self.context.get("request"),
            username=login,
            password=password
        )


        if not user:

            raise AuthenticationFailed("Invalid credentials")


        if not user.is_active:

            raise AuthenticationFailed("User inactive")


        refresh = self.get_token(user)


        return {

            "refresh": str(refresh),

            "access": str(refresh.access_token),

        }
