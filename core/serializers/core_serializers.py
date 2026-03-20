"""
Serializers pour les entités core (AnneeAcademique, Periode, etc.).
"""

from rest_framework import serializers
from core.models import Ecole, AnneeAcademique, Periode, ReglePromotion
from academics.models import Classe


class EcoleSerializer(serializers.ModelSerializer):
    """Serializer pour la configuration de l'école."""
    
    class Meta:
        model = Ecole
        fields = [
            'id', 'nom', 'adresse', 'telephone', 'email',
            'site_web', 'logo', 'devise', 'description',
            'week_type', 'allow_discount',
            'teacher_discount_percent', 'siblings_discount_percent', 'siblings_min_count',
            # ── Paramètres RH (paie du personnel) ─────────────────────────────
            'taux_retenue_absence_defaut',
            'taux_heure_supplementaire_defaut',
            # ── Paramètres horaires ────────────────────────────────────────────
            'heure_debut_cours', 'duree_heure_etude',
            'heure_recreation_apres', 'duree_recreation',
            'actif', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnneeAcademiqueSerializer(serializers.ModelSerializer):
    """Serializer pour les années académiques."""
    
    est_active = serializers.BooleanField(read_only=True)
    nombre_periodes = serializers.SerializerMethodField()
    nombre_inscriptions = serializers.SerializerMethodField()
    
    class Meta:
        model = AnneeAcademique
        fields = [
            'id', 'nom', 'date_debut', 'date_fin', 'est_active',
            'nombre_periodes', 'nombre_inscriptions',
            'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'est_active', 'created_at', 'updated_at']
    
    def get_nombre_periodes(self, obj):
        annotated = getattr(obj, "nombre_periodes", None)
        if annotated is not None:
            return annotated
        return obj.periodes.count()
    
    def get_nombre_inscriptions(self, obj):
        annotated = getattr(obj, "nombre_inscriptions", None)
        if annotated is not None:
            return annotated
        from admission.models import Inscription
        return Inscription.objects.filter(annee_academique=obj).count()
    
    def validate(self, data):
        # Vérifier que date_fin > date_debut
        if data.get('date_fin') and data.get('date_debut'):
            if data['date_fin'] <= data['date_debut']:
                raise serializers.ValidationError({
                    'date_fin': 'La date de fin doit être après la date de début'
                })
        
        # Vérifier qu'il n'y a qu'une seule année active
        if self.instance is None:  # Création
            if AnneeAcademique.objects.filter(
                date_debut__lte=data['date_fin'],
                date_fin__gte=data['date_debut']
            ).exists():
                raise serializers.ValidationError(
                    'Cette période chevauche une année académique existante'
                )
        
        return data


class PeriodeSerializer(serializers.ModelSerializer):
    """Serializer pour les périodes/trimestres."""
    
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    est_active = serializers.BooleanField(read_only=True)
    nombre_evaluations = serializers.SerializerMethodField()
    
    class Meta:
        model = Periode
        fields = [
            'id', 'nom', 'annee_academique', 'annee_nom',
            'date_debut', 'date_fin', 'est_active',
            'nombre_evaluations', 'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'est_active', 'created_at', 'updated_at']
    
    def get_nombre_evaluations(self, obj):
        annotated = getattr(obj, "nombre_evaluations", None)
        if annotated is not None:
            return annotated
        from academics.models import Evaluation
        return Evaluation.objects.filter(periode=obj).count()
    
    def validate(self, data):
        # Vérifier que date_fin > date_debut
        if data.get('date_fin') and data.get('date_debut'):
            if data['date_fin'] <= data['date_debut']:
                raise serializers.ValidationError({
                    'date_fin': 'La date de fin doit être après la date de début'
                })
        
        # Vérifier que la période est dans l'année académique
        if data.get('annee_academique'):
            annee = data['annee_academique']
            if data.get('date_debut') and data.get('date_fin'):
                if not (annee.date_debut <= data['date_debut'] and data['date_fin'] <= annee.date_fin):
                    raise serializers.ValidationError(
                        'La période doit être comprise dans l\'année académique'
                    )
        
        # Vérifier les chevauchements avec d'autres périodes de la même année
        annee_id = data.get('annee_academique').id if data.get('annee_academique') else None
        if annee_id:
            query = Periode.objects.filter(
                annee_academique_id=annee_id,
                date_debut__lte=data.get('date_fin'),
                date_fin__gte=data.get('date_debut')
            )
            
            if self.instance:
                query = query.exclude(id=self.instance.id)
            
            if query.exists():
                raise serializers.ValidationError(
                    'Cette période chevauche une autre période de la même année'
                )
        
        return data


class ReglePromotionSerializer(serializers.ModelSerializer):
    """Serializer pour les règles de promotion."""
    
    classe_origine_nom = serializers.CharField(source='classe_origine.nom', read_only=True)
    classe_destination_nom = serializers.CharField(source='classe_destination.nom', read_only=True)
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    
    class Meta:
        model = ReglePromotion
        fields = [
            'id', 'annee_academique', 'annee_nom',
            'classe_origine', 'classe_origine_nom',
            'classe_destination', 'classe_destination_nom',
            'moyenne_minimale', 'taux_presence_minimal',
            'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Vérifier que moyenne_minimum est entre 0 et 20
        if data.get('moyenne_minimum'):
            if not (0 <= data['moyenne_minimum'] <= 20):
                raise serializers.ValidationError({
                    'moyenne_minimum': 'La moyenne doit être entre 0 et 20'
                })
        
        # Vérifier que taux_presence_minimum est entre 0 et 100
        if data.get('taux_presence_minimum'):
            if not (0 <= data['taux_presence_minimum'] <= 100):
                raise serializers.ValidationError({
                    'taux_presence_minimum': 'Le taux de présence doit être entre 0 et 100'
                })
        
        # Vérifier qu'on ne crée pas de boucle (classe_origine != classe_destination)
        if data.get('classe_origine') and data.get('classe_destination'):
            if data['classe_origine'].id == data['classe_destination'].id:
                raise serializers.ValidationError(
                    'La classe origine et destination doivent être différentes'
                )
        
        return data


class PeriodeListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de périodes."""
    
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    
    class Meta:
        model = Periode
        fields = ['id', 'nom', 'annee_nom', 'date_debut', 'date_fin', 'est_active']


class AnneeAcademiqueListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes d'années."""
    
    class Meta:
        model = AnneeAcademique
        fields = ['id', 'nom', 'date_debut', 'date_fin', 'est_active']
