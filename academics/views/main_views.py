from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from academics.models import Bulletin, Classe, Cours, Evaluation, Note
from academics.permissions.bulletin_permissions import BulletinPermission
from academics.permissions.classes_permissions import ClassePermission
from academics.permissions.cours_permissions import CoursPermission
from academics.permissions.evaluations_permissions import EvaluationPermission
from academics.permissions.note_permissions import NotePermission
from academics.serializers.affectation_serializers import (
    AffectationCreateSerializer, AffectationReadSerializer, AffectationUpdateSerializer
)
from academics.serializers.bulletin_serializers import BulletinReadSerializer
from academics.serializers.classe_serializers import (
    ClasseCreateSerializer, ClasseReadSerializer, ClasseUpdateSerializer
)
from academics.serializers.cours_serializers import (
    CoursCreateSerializer, CoursReadSerializer, CoursUpdateSerializer
)
from academics.serializers.evaluation_serializers import (
    EvaluationCreateSerializer, EvaluationReadSerializer, EvaluationUpdateSerializer
)
from academics.serializers.note_serializers import (
    NoteCreateSerializer, NoteReadSerializer, NoteUpdateSerializer
)
from academics.services.acces_service import AccessService
from academics.services.affectation_services import AffectationService
from academics.services.bulletin_service import BulletinService
from academics.services.classe_service import ClasseService
from academics.services.evaluation_service import EvaluationService
from academics.services.note_service import NoteService
from academics.services.course_service import CoursService
from common.cache_utils import CacheManager
from common.permissions import IsAdmin
from common.role_services import RoleService
from rest_framework.exceptions import PermissionDenied


class ClasseViewSet(ViewSet):
    """
    CRUD des classes.
    Lecture filtré par rôle via AccessService.
    Écriture réservée à l'admin.
    """
    permission_classes = [ClassePermission]
    serializer_class = ClasseReadSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return ClasseCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ClasseUpdateSerializer
        return ClasseReadSerializer

    def list(self, request):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("classes_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        queryset = AccessService.get_user_classes(request.user).select_related(
            "annee_academique"
        )
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer_class()(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            CacheManager.set("classes_list", response.data, **cache_key_args, timeout=300)
            return response
        serializer = self.get_serializer_class()(queryset, many=True)
        response = Response(serializer.data)
        CacheManager.set("classes_list", response.data, **cache_key_args, timeout=300)
        return response

    def retrieve(self, request, pk=None):
        classe = ClasseService.get(pk)
        self.check_object_permissions(request, classe)
        serializer = self.get_serializer_class()(classe)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        classe = ClasseService.create(serializer.validated_data)
        CacheManager.invalidate_pattern("classes_list:*")
        return Response(
            ClasseReadSerializer(classe).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        classe = ClasseService.get(pk)
        self.check_object_permissions(request, classe)
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        classe = ClasseService.update(pk, serializer.validated_data)
        CacheManager.invalidate_pattern("classes_list:*")
        return Response(ClasseReadSerializer(classe).data)

    def destroy(self, request, pk=None):
        classe = ClasseService.get(pk)
        self.check_object_permissions(request, classe)
        ClasseService.delete(pk)
        CacheManager.invalidate_pattern("classes_list:*")
        return Response(status=status.HTTP_204_NO_CONTENT)


class CoursViewSet(ViewSet):
    """
    CRUD des cours.
    Lecture filtré par rôle via AccessService.
    Écriture réservée à l'admin.
    """
    permission_classes = [CoursPermission]
    serializer_class = CoursReadSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return CoursCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CoursUpdateSerializer
        return CoursReadSerializer

    def list(self, request):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("cours_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        queryset = (
            AccessService.get_user_courses(request.user)
            .select_related(
                "classe",
                "annee_academique",
            )
            .prefetch_related(
                "affectations__teacher__user"
            )
        )
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer_class()(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            CacheManager.set("cours_list", response.data, **cache_key_args, timeout=300)
            return response
        serializer = self.get_serializer_class()(queryset, many=True)
        response = Response(serializer.data)
        CacheManager.set("cours_list", response.data, **cache_key_args, timeout=300)
        return response

    def retrieve(self, request, pk=None):
        cours = CoursService.get(pk)
        self.check_object_permissions(request, cours)
        serializer = self.get_serializer_class()(cours)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        cours = CoursService.create(serializer.validated_data)
        CacheManager.invalidate_pattern("cours_list:*")
        return Response(
            CoursReadSerializer(cours).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        cours = CoursService.get(pk)
        self.check_object_permissions(request, cours)
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        cours = CoursService.update(pk, serializer.validated_data)
        CacheManager.invalidate_pattern("cours_list:*")
        return Response(CoursReadSerializer(cours).data)

    def destroy(self, request, pk=None):
        cours = CoursService.get(pk)
        self.check_object_permissions(request, cours)
        CoursService.delete(pk)
        CacheManager.invalidate_pattern("cours_list:*")
        return Response(status=status.HTTP_204_NO_CONTENT)


class NoteViewSet(ViewSet):
    """
    CRUD des notes.
    - Lecture : filtré par rôle (AccessService)
    - Création : enseignant (sur ses cours)
    - Modification : admin uniquement (enseignant interdit)
    """
    permission_classes = [NotePermission]
    serializer_class = NoteReadSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return NoteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return NoteUpdateSerializer
        return NoteReadSerializer

    def list(self, request):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("notes_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        queryset = AccessService.get_user_notes(request.user).select_related(
            "eleve__user",
            "evaluation__cours",
            "evaluation__periode",
            "evaluation__annee_academique"
        )
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer_class()(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            CacheManager.set("notes_list", response.data, **cache_key_args, timeout=300)
            return response
        serializer = self.get_serializer_class()(queryset, many=True)
        response = Response(serializer.data)
        CacheManager.set("notes_list", response.data, **cache_key_args, timeout=300)
        return response

    def retrieve(self, request, pk=None):
        note = NoteService.get(pk)
        self.check_object_permissions(request, note)
        serializer = self.get_serializer_class()(note)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = NoteService.create(serializer.validated_data)
        CacheManager.invalidate_pattern("notes_list:*")
        return Response(
            NoteReadSerializer(note).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        note = NoteService.get(pk)
        self.check_object_permissions(request, note)
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = NoteService.update(pk, serializer.validated_data)
        CacheManager.invalidate_pattern("notes_list:*")
        return Response(NoteReadSerializer(note).data)

    def destroy(self, request, pk=None):
        note = NoteService.get(pk)
        self.check_object_permissions(request, note)
        NoteService.delete(pk)
        CacheManager.invalidate_pattern("notes_list:*")
        return Response(status=status.HTTP_204_NO_CONTENT)


class EvaluationViewSet(ViewSet):
    """
    CRUD des évaluations.
    - Lecture : filtré par rôle (AccessService)
    - Création : enseignant (sur ses cours) ou admin
    - Modification/Suppression : admin uniquement
    """
    permission_classes = [EvaluationPermission]
    serializer_class = EvaluationReadSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return EvaluationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EvaluationUpdateSerializer
        return EvaluationReadSerializer

    def list(self, request):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("evaluations_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        queryset = AccessService.get_user_evaluations(request.user).select_related(
            "cours",
            "periode",
            "annee_academique",
        )
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer_class()(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            CacheManager.set("evaluations_list", response.data, **cache_key_args, timeout=300)
            return response
        serializer = self.get_serializer_class()(queryset, many=True)
        response = Response(serializer.data)
        CacheManager.set("evaluations_list", response.data, **cache_key_args, timeout=300)
        return response

    def retrieve(self, request, pk=None):
        evaluation = EvaluationService.get(pk)
        self.check_object_permissions(request, evaluation)
        serializer = self.get_serializer_class()(evaluation)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluation = EvaluationService.create(serializer.validated_data)
        CacheManager.invalidate_pattern("evaluations_list:*")
        return Response(
            EvaluationReadSerializer(evaluation).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        evaluation = EvaluationService.get(pk)
        self.check_object_permissions(request, evaluation)
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        evaluation = EvaluationService.update(pk, serializer.validated_data)
        CacheManager.invalidate_pattern("evaluations_list:*")
        return Response(EvaluationReadSerializer(evaluation).data)

    def destroy(self, request, pk=None):
        evaluation = EvaluationService.get(pk)
        self.check_object_permissions(request, evaluation)
        EvaluationService.delete(pk)
        CacheManager.invalidate_pattern("evaluations_list:*")
        return Response(status=status.HTTP_204_NO_CONTENT)


class AffectationViewSet(ViewSet):
    """
    CRUD des affectations enseignant-cours.
    Réservé à l'admin.
    """
    permission_classes = [IsAdmin]
    serializer_class = AffectationReadSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return AffectationCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AffectationUpdateSerializer
        return AffectationReadSerializer

    def list(self, request):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("affectations_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        queryset = AffectationService.list().select_related(
            "teacher__user",
            "cours",
        )
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer_class()(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            CacheManager.set("affectations_list", response.data, **cache_key_args, timeout=300)
            return response
        serializer = self.get_serializer_class()(queryset, many=True)
        response = Response(serializer.data)
        CacheManager.set("affectations_list", response.data, **cache_key_args, timeout=300)
        return response

    def retrieve(self, request, pk=None):
        affectation = AffectationService.get(pk)
        self.check_object_permissions(request, affectation)
        serializer = self.get_serializer_class()(affectation)
        return Response(serializer.data)

    def create(self, request):
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        affectation = AffectationService.create(serializer.validated_data)
        CacheManager.invalidate_pattern("affectations_list:*")
        return Response(
            AffectationReadSerializer(affectation).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, pk=None):
        affectation = AffectationService.get(pk)
        self.check_object_permissions(request, affectation)
        serializer = self.get_serializer_class()(data=request.data)
        serializer.is_valid(raise_exception=True)
        affectation = AffectationService.update(pk, serializer.validated_data)
        CacheManager.invalidate_pattern("affectations_list:*")
        return Response(AffectationReadSerializer(affectation).data)

    def destroy(self, request, pk=None):
        affectation = AffectationService.get(pk)
        self.check_object_permissions(request, affectation)
        AffectationService.delete(pk)
        CacheManager.invalidate_pattern("affectations_list:*")
        return Response(status=status.HTTP_204_NO_CONTENT)


class BulletinViewSet(ViewSet):
    """
    Lecture et génération des bulletins.
    - Lecture : filtré par rôle (AccessService)
    - Génération (POST 'generate') : admin uniquement via BulletinService
    """
    permission_classes = [BulletinPermission]
    serializer_class = BulletinReadSerializer

    def get_serializer_class(self):
        return BulletinReadSerializer

    def list(self, request):
        cache_key_args = {
            "user_id": getattr(request.user, "id", None),
            "params": dict(request.query_params),
        }
        cached = CacheManager.get("bulletins_list", **cache_key_args)
        if cached is not None:
            return Response(cached)

        queryset = AccessService.get_user_bulletins(request.user).select_related(
            "eleve__user",
            "classe",
            "periode",
            "annee_academique",
        )
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(queryset, request)
        if page is not None:
            serializer = self.get_serializer_class()(page, many=True)
            response = paginator.get_paginated_response(serializer.data)
            CacheManager.set("bulletins_list", response.data, **cache_key_args, timeout=300)
            return response
        serializer = self.get_serializer_class()(queryset, many=True)
        response = Response(serializer.data)
        CacheManager.set("bulletins_list", response.data, **cache_key_args, timeout=300)
        return response

    def retrieve(self, request, pk=None):
        bulletin = BulletinService.get(pk)
        self.check_object_permissions(request, bulletin)
        serializer = self.get_serializer_class()(bulletin)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Génère un bulletin via BulletinService (admin uniquement)."""
        if not RoleService.is_admin(request.user):
            raise PermissionDenied("Seul l'administrateur peut générer un bulletin.")

        eleve_id = request.data.get("eleve")
        periode_id = request.data.get("periode")

        if not eleve_id or not periode_id:
            return Response(
                {"error": "Les champs 'eleve' et 'periode' sont requis."},
                status=status.HTTP_400_BAD_REQUEST
            )

        from users.models import Eleve
        from core.models import Periode
        from academics.tasks import generate_bulletin_task

        try:
            Eleve.objects.only("id").get(id=eleve_id)
        except Eleve.DoesNotExist:
            return Response({"error": "Élève introuvable."}, status=status.HTTP_404_NOT_FOUND)

        try:
            Periode.objects.only("id").get(id=periode_id)
        except Periode.DoesNotExist:
            return Response({"error": "Période introuvable."}, status=status.HTTP_404_NOT_FOUND)

        task = generate_bulletin_task.delay(eleve_id, periode_id, request.user.id)
        return Response(
            {
                "task_id": task.id,
                "status": "queued",
                "eleve_id": eleve_id,
                "periode_id": periode_id,
            },
            status=status.HTTP_202_ACCEPTED,
        )
