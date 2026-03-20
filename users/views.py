from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from common.permissions import IsAdmin, IsStaffOrDirector
from users.models import Parent, Personnel
from users.services.parent_service import ParentService
from users.services.personnel_service import PersonnelService
from common.role_services import RoleService
from users.services.user_services import UserService
from .serializers import CustomTokenSerializer, ParentCreateSerializer, ParentSerializer, ParentUpdateSerializer, PersonnelCreateSerializer, PersonnelSerializer, PersonnelUpdateSerializer, ProfileSerializer
from rest_framework.permissions import IsAuthenticated

from django.conf import settings
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate

secure_cookie = not settings.DEBUG

class LoginView(APIView):
    authentication_classes = []   # CRITIQUE
    permission_classes = [AllowAny]
    serializer_class = CustomTokenSerializer

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        
        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is None:
            return Response(
                {"error": "Invalid credentials"},
                status=401
            )

        refresh = RefreshToken.for_user(user)

        response = Response({"success": True})

        response.set_cookie(
            "access_token",
            str(refresh.access_token),
            httponly=True,
            secure=secure_cookie,
            samesite="Lax",
        )

        response.set_cookie(
            "refresh_token",
            str(refresh),
            httponly=True,
            secure=secure_cookie,
            samesite="Lax",
        )

        return response



class LogoutView(APIView):
    serializer_class = None

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        response = Response()
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response



class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProfileSerializer

    def get(self, request):
        serializer = self.get_serializer_class()(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = self.get_serializer_class()(
            request.user,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def get_serializer_class(self):
        return ProfileSerializer

class RefreshView(APIView):
    serializer_class = None

    def post(self, request):
        refresh_token = request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(status=401)

        refresh = RefreshToken(refresh_token)
        access_token = refresh.access_token

        response = Response()
        response.set_cookie(
            "access_token",
            str(access_token),
            httponly=True,
            secure=secure_cookie,
            samesite="Lax",
        )

        return response


class PersonnelViewSet(ViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PersonnelSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return PersonnelCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PersonnelUpdateSerializer
        return PersonnelSerializer

    def retrieve(self, request, pk=None):
        personnel = Personnel.objects.select_related("user").get(id=pk)
        serializer = self.get_serializer_class()(personnel)
        return Response(serializer.data)

    def list(self, request):
        queryset = Personnel.objects.select_related("user")
        serializer = self.get_serializer_class()(queryset, many=True)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        personnel, password = PersonnelService.create(serializer.validated_data)
        return Response(
            PersonnelSerializer(personnel).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        personnel = PersonnelService.update(pk, serializer.validated_data)
        return Response(
            PersonnelSerializer(personnel).data
        )

    def destroy(self, request, pk=None):
        if not RoleService.is_admin(request.user):
            return Response(status=403)
        PersonnelService.delete(pk)
        return Response(status=204)
  
    
class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "email": request.user.email,
            "roles": RoleService.roles(request.user),
        })

class ParentViewSet(ViewSet):
    serializer_class = ParentSerializer

    def get_permissions(self):
        if self.action == "create":
            return [IsStaffOrDirector()]
        if self.action == "list":
            return [IsStaffOrDirector()]
        if self.action == "retrieve":
            return [IsStaffOrDirector()]
        if self.action == "update":
            return [IsStaffOrDirector()]
        if self.action == "destroy":
            return [IsAdmin()]
        if self.action in ["add_student", "remove_student"]:
            return [IsStaffOrDirector()]
        return super().get_permissions()

    def get_queryset(self):
        return Parent.objects.with_user().active()

    def get_serializer_class(self):
        if self.action == 'create':
            return ParentCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ParentUpdateSerializer
        return ParentSerializer

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer_class()(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        parent = self.get_queryset().get(id=pk)
        serializer = self.get_serializer_class()(parent)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent, password = ParentService.create(serializer.validated_data)
        return Response(
            {
                "parent": ParentSerializer(parent).data,
                "temporary_password": password
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        parent = ParentService.update(pk, serializer.validated_data)
        return Response(
            ParentSerializer(parent).data
        )

    def destroy(self, request, pk=None):
        ParentService.delete(pk)
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def add_student(self, request, pk=None):
        eleve_id = request.data["eleve_id"]
        reduction = request.data.get("reduction_percent", 0)
        relation = ParentService.add_student(pk, eleve_id, reduction)
        return Response(status=200)

    @action(detail=True, methods=["post"])
    def remove_student(self, request, pk=None):
        eleve_id = request.data["eleve_id"]
        ParentService.remove_student(pk, eleve_id)
        return Response(status=204)

    @action(detail=False, methods=["get"])
    def me(self, request):
        parent = request.user.parent_profile
        return Response(
            ParentSerializer(parent).data
        )




from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from users.services.dashboard_aggregator import DashboardAggregatorService

class MyDashboardView(APIView):
    """
    Endpoint consolidé: GET /api/v1/users/me/dashboard/
    Retourne TOUTES les informations pertinentes pour l'utilisateur connecté selon son/ses rôle(s).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        service = DashboardAggregatorService(request.user)
        dashboard_data = service.get_dashboard_data()
        return Response(dashboard_data)
