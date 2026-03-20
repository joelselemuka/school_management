"""
Serializers pour la gestion des examens et des salles.
"""

from rest_framework import serializers
from academics.models import Salle, SessionExamen, PlanificationExamen, RepartitionExamen, Evaluation
from users.models import Personnel, Eleve


class SalleSerializer(serializers.ModelSerializer):
    """Serializer pour les salles."""
    
    places_disponibles = serializers.ReadOnlyField()
    
    class Meta:
        model = Salle
        fields = [
            'id', 'code', 'nom', 'batiment', 'capacite', 
            'type_salle', 'equipements', 'est_disponible',
            'places_disponibles', 'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'places_disponibles']
    
    def validate_capacite(self, value):
        if value <= 0:
            raise serializers.ValidationError("La capacité doit être supérieure à 0")
        return value


class SalleListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de salles."""
    
    class Meta:
        model = Salle
        fields = ['id', 'code', 'nom', 'capacite', 'type_salle', 'est_disponible']


class SessionExamenSerializer(serializers.ModelSerializer):
    """Serializer pour les sessions d'examen."""
    
    periode_nom = serializers.CharField(source='periode.nom', read_only=True)
    nombre_planifications = serializers.SerializerMethodField()
    
    class Meta:
        model = SessionExamen
        fields = [
            'id', 'nom', 'periode', 'periode_nom', 'date_debut', 'date_fin',
            'type_session', 'instructions', 'statut', 'nombre_planifications',
            'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'nombre_planifications']
    
    def get_nombre_planifications(self, obj):
        annotated = getattr(obj, "nombre_planifications", None)
        if annotated is not None:
            return annotated
        return obj.planifications.count()
    
    def validate(self, data):
        if data.get('date_fin') and data.get('date_debut'):
            if data['date_fin'] <= data['date_debut']:
                raise serializers.ValidationError({
                    'date_fin': 'La date de fin doit être après la date de début'
                })
        return data


class PlanificationExamenSerializer(serializers.ModelSerializer):
    """Serializer pour la planification des examens."""
    
    evaluation_nom = serializers.CharField(source='evaluation.nom', read_only=True)
    cours_nom = serializers.CharField(source='evaluation.cours.nom', read_only=True)
    salle_code = serializers.CharField(source='salle.code', read_only=True)
    salle_nom = serializers.CharField(source='salle.nom', read_only=True)
    session_nom = serializers.CharField(source='session_examen.nom', read_only=True, allow_null=True)
    nombre_repartitions = serializers.SerializerMethodField()
    surveillants_details = serializers.SerializerMethodField()
    
    class Meta:
        model = PlanificationExamen
        fields = [
            'id', 'evaluation', 'evaluation_nom', 'cours_nom',
            'session_examen', 'session_nom', 'salle', 'salle_code', 'salle_nom',
            'date_examen', 'heure_debut', 'heure_fin', 'duree_minutes',
            'surveillants', 'surveillants_details', 'instructions_surveillants',
            'nombre_repartitions', 'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'nombre_repartitions']
    
    def get_nombre_repartitions(self, obj):
        if hasattr(obj, "_prefetched_objects_cache") and "repartitions" in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache["repartitions"])
        return obj.repartitions.count()
    
    def get_surveillants_details(self, obj):
        return [
            {
                'id': s.id,
                'nom': s.nom,
                'postnom': s.postnom,
                'prenom': s.prenom,
                'matricule': s.user.matricule if hasattr(s, 'user') else None
            }
            for s in obj.surveillants.all()
        ]
    
    def validate(self, data):
        # Validation des heures
        if data.get('heure_fin') and data.get('heure_debut'):
            if data['heure_fin'] <= data['heure_debut']:
                raise serializers.ValidationError({
                    'heure_fin': "L'heure de fin doit être après l'heure de début"
                })
        
        # Validation de la date d'examen
        if data.get('evaluation') and data.get('date_examen'):
            evaluation = data['evaluation']
            date_examen = data['date_examen']
            periode = evaluation.periode
            
            if not (periode.date_debut <= date_examen <= periode.date_fin):
                raise serializers.ValidationError({
                    'date_examen': 'La date doit être dans la période de l\'évaluation'
                })
        
        return data


class PlanificationExamenListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de planifications."""
    
    evaluation_nom = serializers.CharField(source='evaluation.nom', read_only=True)
    salle_code = serializers.CharField(source='salle.code', read_only=True)
    
    class Meta:
        model = PlanificationExamen
        fields = [
            'id', 'evaluation_nom', 'salle_code', 'date_examen',
            'heure_debut', 'heure_fin'
        ]


class RepartitionExamenSerializer(serializers.ModelSerializer):
    """Serializer pour la répartition des élèves."""
    
    eleve_nom_complet = serializers.SerializerMethodField()
    eleve_matricule = serializers.CharField(source='eleve.user.matricule', read_only=True)
    planification_details = serializers.SerializerMethodField()
    
    class Meta:
        model = RepartitionExamen
        fields = [
            'id', 'planification', 'planification_details', 'eleve', 
            'eleve_nom_complet', 'eleve_matricule', 'numero_place',
            'zone', 'rangee', 'colonne', 'instructions_speciales',
            'est_present', 'heure_arrivee', 'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_eleve_nom_complet(self, obj):
        return f"{obj.eleve.nom} {obj.eleve.postnom} {obj.eleve.prenom}"
    
    def get_planification_details(self, obj):
        return {
            'id': obj.planification.id,
            'salle': obj.planification.salle.code,
            'date': obj.planification.date_examen,
            'heure_debut': obj.planification.heure_debut
        }


class RepartitionExamenListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de répartitions."""
    
    eleve_nom = serializers.CharField(source='eleve.nom', read_only=True)
    salle_code = serializers.CharField(source='planification.salle.code', read_only=True)
    
    class Meta:
        model = RepartitionExamen
        fields = [
            'id', 'eleve_nom', 'salle_code', 'numero_place', 'est_present'
        ]


class ExamDistributionRequestSerializer(serializers.Serializer):
    """Serializer pour les requêtes de génération de répartition."""
    
    evaluation_id = serializers.IntegerField(required=True)
    salle_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=True,
        min_length=1
    )
    max_students_per_class_per_room = serializers.IntegerField(
        default=5,
        min_value=1,
        max_value=50
    )
    spacing_strategy = serializers.ChoiceField(
        choices=['alternate', 'grouped', 'random'],
        default='alternate'
    )
    clear_existing = serializers.BooleanField(default=True)
    
    def validate_evaluation_id(self, value):
        if not Evaluation.objects.filter(id=value).exists():
            raise serializers.ValidationError("Évaluation introuvable")
        return value
    
    def validate_salle_ids(self, value):
        salles = Salle.objects.filter(id__in=value, est_disponible=True, actif=True)
        if salles.count() != len(value):
            raise serializers.ValidationError("Une ou plusieurs salles sont invalides ou non disponibles")
        return value


class ExamDistributionResponseSerializer(serializers.Serializer):
    """Serializer pour les réponses de génération de répartition."""
    
    total_students = serializers.IntegerField()
    total_rooms = serializers.IntegerField()
    summary = serializers.ListField(
        child=serializers.DictField()
    )
    message = serializers.CharField()


class PresenceMarkerSerializer(serializers.Serializer):
    """Serializer pour marquer la présence d'un élève."""
    
    repartition_id = serializers.IntegerField(required=True)
    heure_arrivee = serializers.DateTimeField(required=False, allow_null=True)
    
    def validate_repartition_id(self, value):
        if not RepartitionExamen.objects.filter(id=value).exists():
            raise serializers.ValidationError("Répartition introuvable")
        return value
