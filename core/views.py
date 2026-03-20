
from common.permissions import IsAdmin
from core.models import AnneeAcademique, Periode
from core.serializers.annee_serialisers import (
    AnneeAcademiqueReadSerializer, AnneeAcademiqueWriteSerializer
)
from core.serializers.periode_serializers import (
    PeriodeReadSerializer, PeriodeWriteSerializer
)
from core.services.annee_academique_service import AnneeAcademiqueService
from core.services.periode_services import PeriodeService
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet
from drf_spectacular.utils import extend_schema, extend_schema_view


@extend_schema_view(
    list=extend_schema(
        summary="Lister les années académiques",
        tags=["Core"]
    ),
    create=extend_schema(
        summary="Créer une année académique",
        description="Permet d'enregistrer une nouvelle année académique dans l'école",
        tags=["Core"]
    ),
    retrieve=extend_schema(
        summary="Détail d'une année académique",
        tags=["Core"]
    ),
    update=extend_schema(
        summary="Modifier une année académique",
        tags=["Core"]
    ),
    destroy=extend_schema(
        summary="Supprimer une année académique",
        tags=["Core"]
    ),
)
class AnneeAcademiqueViewSet(ModelViewSet):
    """ViewSet pour la gestion des années académiques."""

    queryset = AnneeAcademique.objects.all()
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return AnneeAcademiqueWriteSerializer
        return AnneeAcademiqueReadSerializer

    def perform_create(self, serializer):
        serializer.instance = AnneeAcademiqueService.create(
            **serializer.validated_data
        )

    def perform_update(self, serializer):
        serializer.instance = AnneeAcademiqueService.update(
            self.get_object(),
            **serializer.validated_data
        )

    def perform_destroy(self, instance):
        AnneeAcademiqueService.delete(instance)


@extend_schema_view(
    list=extend_schema(summary="Lister les périodes", tags=["Core"]),
    create=extend_schema(summary="Créer une période", tags=["Core"]),
    retrieve=extend_schema(summary="Détail d'une période", tags=["Core"]),
    update=extend_schema(summary="Modifier une période", tags=["Core"]),
    destroy=extend_schema(summary="Supprimer une période", tags=["Core"]),
)
class PeriodeViewSet(ModelViewSet):
    """ViewSet pour la gestion des périodes (trimestres, semestres)."""

    queryset = Periode.objects.select_related("annee_academique")
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return PeriodeWriteSerializer
        return PeriodeReadSerializer

    def perform_create(self, serializer):
        serializer.instance = PeriodeService.create(
            **serializer.validated_data
        )

    def perform_update(self, serializer):
        serializer.instance = PeriodeService.update(
            self.get_object(),
            **serializer.validated_data
        )

    def perform_destroy(self, instance):
        PeriodeService.delete(instance)