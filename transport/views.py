from rest_framework import viewsets, views
from rest_framework.response import Response
from transport.models import Bus, ArretBus, Itineraire, ArretItineraire, AffectationEleveTransport, AffectationChauffeur
from transport.serializers import (
    BusSerializer, ArretBusSerializer, ItineraireSerializer,
    ArretItineraireSerializer, AffectationEleveTransportSerializer,
    AffectationChauffeurSerializer
)
from common.permissions import CanManageTransport

class BusViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageTransport]
    queryset = Bus.objects.filter(actif=True)
    serializer_class = BusSerializer
    filterset_fields = ['est_operationnel']

class ArretBusViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageTransport]
    queryset = ArretBus.objects.filter(actif=True)
    serializer_class = ArretBusSerializer

class ItineraireViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageTransport]
    queryset = Itineraire.objects.filter(actif=True).select_related('annee_academique')
    serializer_class = ItineraireSerializer
    filterset_fields = ['annee_academique']

class ArretItineraireViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageTransport]
    queryset = ArretItineraire.objects.all().select_related('itineraire', 'arret')
    serializer_class = ArretItineraireSerializer
    filterset_fields = ['itineraire', 'arret']

class AffectationEleveTransportViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageTransport]
    queryset = AffectationEleveTransport.objects.filter(actif=True).select_related('eleve__user', 'itineraire', 'arret_montee', 'arret_descente', 'annee_academique')
    serializer_class = AffectationEleveTransportSerializer
    filterset_fields = ['eleve', 'itineraire', 'annee_academique']


class AffectationChauffeurViewSet(viewsets.ModelViewSet):
    permission_classes = [CanManageTransport]
    queryset = AffectationChauffeur.objects.filter(actif=True).select_related('chauffeur__user', 'bus', 'itineraire', 'annee_academique')
    serializer_class = AffectationChauffeurSerializer
    filterset_fields = ['chauffeur', 'bus', 'itineraire', 'annee_academique']



class DashboardChauffeurView(views.APIView):
    """
    Dashboard dédié au chauffeur: liste les itinéraires de son bus et les élèves à récupérer.
    """
    from common.permissions import IsDriver
    permission_classes = [IsDriver]

    def get(self, request):
        chauffeur = getattr(request.user, 'personnel_profile', None)
        if not chauffeur:
            return Response({"detail": "Profil chauffeur introuvable."}, status=404)
            
        affectations_chauffeur = AffectationChauffeur.objects.filter(chauffeur=chauffeur, actif=True)
        itineraires = [a.itineraire for a in affectations_chauffeur]
        
        affectations = AffectationEleveTransport.objects.filter(
            itineraire__in=itineraires,
            actif=True
        )
        
        # We process the serializers individually due to list comprehension
        itineraires_data = ItineraireSerializer(itineraires, many=True).data
        
        return Response({
            "chauffeur": chauffeur.full_name,
            "mes_affectations": AffectationChauffeurSerializer(affectations_chauffeur, many=True).data,
            "itineraires": itineraires_data,
            "eleves_a_bord": AffectationEleveTransportSerializer(affectations, many=True).data
        })

