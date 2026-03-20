from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
import uuid

from bibliotheque.models import Livre, Exemplaire, Emprunt, PaiementAmende, Inventaire, LigneInventaire
from bibliotheque.serializers import (
    LivreSerializer, ExemplaireSerializer, EmpruntSerializer,
    PaiementAmendeSerializer, InventaireSerializer, LigneInventaireSerializer
)
from bibliotheque.services.livre_service import LivreService
from bibliotheque.services.exemplaire_service import ExemplaireService
from bibliotheque.services.inventaire_service import InventaireService
from bibliotheque.services.emprunt_service import EmpruntService
from common.permissions import CanManageLibrary

class LivreViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageLibrary]
    queryset = Livre.objects.filter(actif=True)
    serializer_class = LivreSerializer

    def perform_create(self, serializer):
        serializer.instance = LivreService.create_livre(serializer.validated_data)

    def perform_update(self, serializer):
        serializer.instance = LivreService.update_livre(self.get_object(), serializer.validated_data)

class ExemplaireViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageLibrary]
    queryset = Exemplaire.objects.filter(actif=True).select_related('livre', 'date_acquisition')
    serializer_class = ExemplaireSerializer
    filterset_fields = ['livre', 'etat', 'est_disponible']

    def perform_create(self, serializer):
        serializer.instance = ExemplaireService.create_exemplaire(serializer.validated_data)

    def perform_update(self, serializer):
        serializer.instance = ExemplaireService.update_exemplaire(self.get_object(), serializer.validated_data)

class EmpruntViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageLibrary]
    queryset = Emprunt.objects.all().select_related('exemplaire__livre', 'emprunteur__user')
    serializer_class = EmpruntSerializer
    filterset_fields = ['exemplaire', 'emprunteur', 'statut']

    def perform_create(self, serializer):
        serializer.instance = EmpruntService.create_emprunt(serializer.validated_data, self.request.user)

    @action(detail=True, methods=['post'])
    def retourner(self, request, pk=None):
        emprunt = self.get_object()
        if emprunt.statut not in ["EN_COURS", "EN_RETARD"]:
            return Response(
                {"detail": "Cet emprunt n'est plus en cours ou est déjà retourné."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        emprunt = EmpruntService.retourner_livre(emprunt, request.user, request.data)
        return Response(EmpruntSerializer(emprunt).data)

    @action(detail=True, methods=['post'])
    def prolonger(self, request, pk=None):
        emprunt = self.get_object()
        nouvelle_date = request.data.get("nouvelle_date_retour")
        
        if not nouvelle_date:
            return Response(
                {"detail": "La nouvelle date de retour est requise."},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        emprunt = EmpruntService.prolonger_emprunt(emprunt, nouvelle_date)
        return Response(EmpruntSerializer(emprunt).data)


class PaiementAmendeViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageLibrary]
    queryset = PaiementAmende.objects.all().select_related('emprunt__emprunteur__user', 'emprunt__exemplaire', 'percu_par')
    serializer_class = PaiementAmendeSerializer
    filterset_fields = ['emprunt', 'emprunt__emprunteur']

    def perform_create(self, serializer):
        ref = f"AMB-{uuid.uuid4().hex[:8].upper()}"
        serializer.save(percu_par=self.request.user, reference=ref)


class InventaireViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageLibrary]
    queryset = Inventaire.objects.all().select_related('cree_par', 'cloture_par')
    serializer_class = InventaireSerializer

    def perform_create(self, serializer):
        serializer.instance = InventaireService.create_inventaire(serializer.validated_data, self.request.user)

    def perform_update(self, serializer):
        serializer.instance = InventaireService.update_inventaire(self.get_object(), serializer.validated_data)

    @action(detail=True, methods=['post'])
    def cloturer(self, request, pk=None):
        inventaire = self.get_object()
        inventaire = InventaireService.cloturer_inventaire(inventaire)
        return Response(InventaireSerializer(inventaire).data)

    @action(detail=True, methods=['get'])
    def rapport(self, request, pk=None):
        inventaire = self.get_object()
        rapport_data = InventaireService.generer_rapport(inventaire)
        return Response(rapport_data)
