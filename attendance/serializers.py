"""
Serializers pour la gestion des présences et horaires.
"""

from rest_framework import serializers
from attendance.models import (
    HoraireCours, SeanceCours, Presence, JustificationAbsence,
    DisciplineRecord, AttendanceSummary, Holiday, AcademicCalendarEvent,
    ClasseHoraireConfig, HoraireEnseignant,
)
from academics.models import Cours, Classe
from core.models import AnneeAcademique, Periode
from users.models import Eleve, Personnel


class HoraireSerializer(serializers.ModelSerializer):
    """Serializer pour les horaires de cours."""

    cours_nom = serializers.CharField(source='cours.nom', read_only=True)
    classe_nom = serializers.CharField(source='classe.nom', read_only=True)
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    volume_horaire = serializers.IntegerField(source='cours.volume_horaire', read_only=True)
    plage_horaire = serializers.SerializerMethodField()

    class Meta:
        model = HoraireCours
        fields = [
            'id', 'cours', 'cours_nom', 'volume_horaire', 'classe', 'classe_nom',
            'annee_academique', 'annee_nom', 'salle', 'jour',
            'numero_heure', 'heure_debut', 'heure_fin', 'plage_horaire',
            'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'heure_debut', 'heure_fin', 'plage_horaire', 'created_at', 'updated_at']

    def get_plage_horaire(self, obj):
        """Retourne la plage horaire formatée. Ex: '07h30 – 08h20'"""
        if obj.heure_debut and obj.heure_fin:
            return (
                f"{obj.heure_debut.strftime('%Hh%M')} – "
                f"{obj.heure_fin.strftime('%Hh%M')}"
            )
        return None

    def validate(self, data):
        # Vérifier que heure_fin > heure_debut si renseignées manuellement
        if data.get('heure_fin') and data.get('heure_debut'):
            if data['heure_fin'] <= data['heure_debut']:
                raise serializers.ValidationError({
                    'heure_fin': "L'heure de fin doit être après l'heure de début"
                })
        return data


class ClasseHoraireConfigSerializer(serializers.ModelSerializer):
    """Serializer pour la configuration horaire d'une classe."""

    classe_nom = serializers.CharField(source='classe.nom', read_only=True)
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    slots_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = ClasseHoraireConfig
        fields = [
            'id', 'classe', 'classe_nom', 'annee_academique', 'annee_nom',
            'heures_max_par_jour', 'jours_prolonges', 'slots_disponibles',
        ]
        read_only_fields = ['id', 'slots_disponibles']

    def get_slots_disponibles(self, obj):
        """Calcule le total de créneaux par semaine pour cette classe."""
        from attendance.services.horaire_generation_service import JOURS_ORDRE
        from common.utils import get_jour_map
        try:
            jour_map = get_jour_map()
            jours_actifs = [j for j in JOURS_ORDRE if j in jour_map]
            jours_prolonges = set(obj.jours_prolonges or [])
            total = 0
            for jour in jours_actifs:
                if obj.heures_max_par_jour <= 6:
                    total += obj.heures_max_par_jour
                else:
                    total += obj.heures_max_par_jour if jour in jours_prolonges else 6
            return total
        except Exception:
            return None

    def validate_jours_prolonges(self, value):
        from attendance.models import JOUR_CHOICES
        jours_valides = {c[0] for c in JOUR_CHOICES}
        for j in value:
            if j not in jours_valides:
                raise serializers.ValidationError(f"Jour invalide: {j}")
        return value


class HoraireEnseignantSerializer(serializers.ModelSerializer):
    """Serializer pour les horaires enseignants."""

    enseignant_nom = serializers.SerializerMethodField()
    cours_nom = serializers.CharField(source='horaire_cours.cours.nom', read_only=True)
    classe_nom = serializers.CharField(source='horaire_cours.classe.nom', read_only=True)
    jour = serializers.CharField(source='horaire_cours.jour', read_only=True)
    numero_heure = serializers.IntegerField(source='horaire_cours.numero_heure', read_only=True)
    heure_debut = serializers.TimeField(source='horaire_cours.heure_debut', read_only=True)
    heure_fin = serializers.TimeField(source='horaire_cours.heure_fin', read_only=True)
    salle = serializers.CharField(source='horaire_cours.salle', read_only=True)
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)

    class Meta:
        model = HoraireEnseignant
        fields = [
            'id', 'enseignant', 'enseignant_nom', 'horaire_cours',
            'annee_academique', 'annee_nom',
            'cours_nom', 'classe_nom', 'jour', 'numero_heure',
            'heure_debut', 'heure_fin', 'salle',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'cours_nom', 'classe_nom', 'jour', 'numero_heure',
            'heure_debut', 'heure_fin', 'salle', 'created_at', 'updated_at'
        ]

    def get_enseignant_nom(self, obj):
        p = obj.enseignant
        return f"{p.nom} {p.prenom}" if hasattr(p, 'prenom') and p.prenom else str(p)


class SeanceSerializer(serializers.ModelSerializer):
    """Serializer pour les séances de cours."""
    
    horaire_details = serializers.SerializerMethodField()
    cours_nom = serializers.CharField(source='cours.nom', read_only=True)
    classe_nom = serializers.CharField(source='classe.nom', read_only=True)
    nombre_presences = serializers.SerializerMethodField()
    
    class Meta:
        model = SeanceCours
        fields = [
            'id', 'horaire', 'horaire_details', 'cours', 'cours_nom',
            'classe', 'classe_nom', 'annee_academique', 'date',
            'is_locked', 'is_holiday', 'type', 'is_suspended',
            'nombre_presences', 'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'nombre_presences']
    
    def get_horaire_details(self, obj):
        if obj.horaire:
            return {
                'jour': obj.horaire.jour,
                'heure_debut': obj.horaire.heure_debut,
                'heure_fin': obj.horaire.heure_fin,
                'salle': obj.horaire.salle
            }
        return None
    
    def get_nombre_presences(self, obj):
        annotated = getattr(obj, "nombre_presences", None)
        if annotated is not None:
            return annotated
        return obj.presences.filter(actif=True).count()


class PresenceSerializer(serializers.ModelSerializer):
    """Serializer pour les présences des élèves."""
    
    eleve_nom_complet = serializers.SerializerMethodField()
    eleve_matricule = serializers.CharField(source='eleve.user.matricule', read_only=True)
    seance_details = serializers.SerializerMethodField()
    has_justification = serializers.SerializerMethodField()
    
    class Meta:
        model = Presence
        fields = [
            'id', 'eleve', 'eleve_nom_complet', 'eleve_matricule',
            'seance', 'seance_details', 'statut', 'remarque',
            'has_justification', 'actif', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'has_justification']
    
    def get_eleve_nom_complet(self, obj):
        return f"{obj.eleve.nom} {obj.eleve.postnom} {obj.eleve.prenom}"
    
    def get_seance_details(self, obj):
        return {
            'id': obj.seance.id,
            'cours': obj.seance.cours.nom,
            'date': obj.seance.date,
            'type': obj.seance.type
        }
    
    def get_has_justification(self, obj):
        return hasattr(obj, 'justificationabsence')


class PresenceListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes de présences."""
    
    eleve_nom = serializers.CharField(source='eleve.nom', read_only=True)
    
    class Meta:
        model = Presence
        fields = ['id', 'eleve_nom', 'statut', 'created_at']


class JustificationAbsenceSerializer(serializers.ModelSerializer):
    """Serializer pour les justifications d'absence."""
    
    presence_details = serializers.SerializerMethodField()
    eleve_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = JustificationAbsence
        fields = [
            'id', 'presence', 'presence_details', 'eleve_nom',
            'motif', 'document', 'valide', 'actif',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_presence_details(self, obj):
        return {
            'id': obj.presence.id,
            'date': obj.presence.seance.date,
            'cours': obj.presence.seance.cours.nom,
            'statut': obj.presence.statut
        }
    
    def get_eleve_nom(self, obj):
        eleve = obj.presence.eleve
        return f"{eleve.nom} {eleve.postnom} {eleve.prenom}"


class AttendanceSummarySerializer(serializers.ModelSerializer):
    """Serializer pour les résumés de présence."""
    
    eleve_nom_complet = serializers.SerializerMethodField()
    eleve_matricule = serializers.CharField(source='eleve.user.matricule', read_only=True)
    periode_nom = serializers.CharField(source='periode.nom', read_only=True)
    taux_presence = serializers.SerializerMethodField()
    
    class Meta:
        model = AttendanceSummary
        fields = [
            'id', 'eleve', 'eleve_nom_complet', 'eleve_matricule',
            'periode', 'periode_nom', 'absences', 'retards',
            'taux_presence', 'is_blocking'
        ]
        read_only_fields = ['id', 'taux_presence']
    
    def get_eleve_nom_complet(self, obj):
        return f"{obj.eleve.nom} {obj.eleve.postnom} {obj.eleve.prenom}"
    
    def get_taux_presence(self, obj):
        # Calculer le taux de présence
        total_seances = obj.periode.seances.filter(
            classe=obj.eleve.inscriptions.first().classe if obj.eleve.inscriptions.exists() else None
        ).count()
        
        if total_seances == 0:
            return 100.0
        
        taux = ((total_seances - obj.absences) / total_seances) * 100
        return round(taux, 2)


class DisciplineRecordSerializer(serializers.ModelSerializer):
    """Serializer pour les enregistrements disciplinaires."""
    
    eleve_nom_complet = serializers.SerializerMethodField()
    
    class Meta:
        model = DisciplineRecord
        fields = [
            'id', 'eleve', 'eleve_nom_complet', 'niveau',
            'date', 'actif', 'created_at'
        ]
        read_only_fields = ['id', 'date', 'created_at']
    
    def get_eleve_nom_complet(self, obj):
        return f"{obj.eleve.nom} {obj.eleve.postnom} {obj.eleve.prenom}"


class HolidaySerializer(serializers.ModelSerializer):
    """Serializer pour les jours fériés."""
    
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    
    class Meta:
        model = Holiday
        fields = ['id', 'date', 'label', 'annee_academique', 'annee_nom']


class AcademicCalendarEventSerializer(serializers.ModelSerializer):
    """Serializer pour les événements du calendrier académique."""
    
    annee_nom = serializers.CharField(source='annee_academique.nom', read_only=True)
    classes_noms = serializers.SerializerMethodField()
    
    class Meta:
        model = AcademicCalendarEvent
        fields = [
            'id', 'annee_academique', 'annee_nom', 'type', 'label',
            'date_debut', 'date_fin', 'classes', 'classes_noms',
            'suspend_cours', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']
    
    def get_classes_noms(self, obj):
        if obj.classes.exists():
            return [c.nom for c in obj.classes.all()]
        return ['Toutes les classes']
    
    def validate(self, data):
        if data.get('date_fin') and data.get('date_debut'):
            if data['date_fin'] < data['date_debut']:
                raise serializers.ValidationError({
                    'date_fin': 'La date de fin doit être après la date de début'
                })
        return data


class BulkPresenceSerializer(serializers.Serializer):
    """Serializer pour marquer les présences en lot."""
    
    seance_id = serializers.IntegerField(required=True)
    presences = serializers.ListField(
        child=serializers.DictField(),
        required=True,
        min_length=1
    )
    
    def validate_seance_id(self, value):
        if not SeanceCours.objects.filter(id=value).exists():
            raise serializers.ValidationError("Séance introuvable")
        return value
    
    def validate_presences(self, value):
        for presence in value:
            if 'eleve_id' not in presence or 'statut' not in presence:
                raise serializers.ValidationError(
                    "Chaque présence doit contenir 'eleve_id' et 'statut'"
                )
        return value
