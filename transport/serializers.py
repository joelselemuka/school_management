from rest_framework import serializers
from transport.models import Bus, ArretBus, Itineraire, ArretItineraire, AffectationEleveTransport, AffectationChauffeur

class BusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bus
        fields = ['id', 'numero', 'immatriculation', 'capacite', 'modele', 'est_operationnel', 'remarques']

class ArretBusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArretBus
        fields = '__all__'

class ArretItineraireSerializer(serializers.ModelSerializer):
    arret_nom = serializers.CharField(source='arret.nom', read_only=True)
    
    class Meta:
        model = ArretItineraire
        fields = ['id', 'itineraire', 'arret', 'arret_nom', 'ordre', 'heure_passage_matin', 'heure_passage_soir']

class ItineraireSerializer(serializers.ModelSerializer):
    arrets = ArretItineraireSerializer(many=True, read_only=True)
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    
    class Meta:
        model = Itineraire
        fields = ['id', 'nom', 'annee_academique', 'annee_nom', 'description', 'actif', 'arrets']

class AffectationEleveTransportSerializer(serializers.ModelSerializer):
    eleve_nom_complet = serializers.CharField(source='eleve.get_full_name', read_only=True)
    itineraire_nom = serializers.CharField(source='itineraire.nom', read_only=True)
    arret_montee_nom = serializers.CharField(source='arret_montee.arret.nom', read_only=True)
    arret_descente_nom = serializers.CharField(source='arret_descente.arret.nom', read_only=True)
    
    class Meta:
        model = AffectationEleveTransport
        fields = [
            'id', 'eleve', 'eleve_nom_complet', 'annee_academique', 'itineraire', 'itineraire_nom',
            'arret_montee', 'arret_montee_nom', 'arret_descente', 'arret_descente_nom',
            'date_affectation', 'actif'
        ]
        read_only_fields = ['date_affectation']


class AffectationChauffeurSerializer(serializers.ModelSerializer):
    chauffeur_nom = serializers.CharField(source='chauffeur.full_name', read_only=True)
    itineraire_nom = serializers.CharField(source='itineraire.nom', read_only=True)
    bus_numero = serializers.CharField(source='bus.numero', read_only=True)
    
    class Meta:
        model = AffectationChauffeur
        fields = ['id', 'chauffeur', 'chauffeur_nom', 'bus', 'bus_numero', 'itineraire', 'itineraire_nom', 'annee_academique', 'date_affectation', 'actif']
        read_only_fields = ['date_affectation']

