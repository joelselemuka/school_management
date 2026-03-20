"""
Serializers pour le module Events.
"""

from rest_framework import serializers
from events.models import Event, Actualite, InscriptionEvenement
from users.serializers import UserSerializer


class EventSerializer(serializers.ModelSerializer):
    """Serializer pour les événements."""
    
    organisateur_details = UserSerializer(source='organisateur', read_only=True)
    est_passe = serializers.BooleanField(read_only=True)
    est_en_cours = serializers.BooleanField(read_only=True)
    nombre_inscrits = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'titre', 'description', 'type_evenement', 'date_debut', 
            'date_fin', 'lieu', 'organisateur', 'organisateur_details', 
            'statut', 'annee_academique', 'participants_attendus', 'image',
            'est_public', 'inscription_requise', 'est_passe', 'est_en_cours',
            'nombre_inscrits', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_nombre_inscrits(self, obj):
        """Retourne le nombre d'inscriptions confirmées."""
        annotated = getattr(obj, "nombre_inscrits", None)
        if annotated is not None:
            return annotated
        return obj.inscriptions.filter(statut='confirme').count()


class EventListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes d'événements."""
    
    organisateur_nom = serializers.SerializerMethodField()
    nombre_inscrits = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'titre', 'type_evenement', 'date_debut', 'date_fin',
            'lieu', 'statut', 'organisateur_nom', 'image', 'est_public',
            'nombre_inscrits'
        ]
    
    def get_organisateur_nom(self, obj):
        """Retourne le nom complet de l'organisateur."""
        if obj.organisateur:
            return obj.organisateur.get_full_name()
        return None
    
    def get_nombre_inscrits(self, obj):
        """Retourne le nombre d'inscriptions confirmées."""
        annotated = getattr(obj, "nombre_inscrits", None)
        if annotated is not None:
            return annotated
        return obj.inscriptions.filter(statut='confirme').count()


class ActualiteSerializer(serializers.ModelSerializer):
    """Serializer pour les actualités."""
    
    auteur_details = UserSerializer(source='auteur', read_only=True)
    est_active = serializers.BooleanField(read_only=True)
    tags_list = serializers.ListField(
        source='get_tags_list',
        read_only=True
    )
    
    class Meta:
        model = Actualite
        fields = [
            'id', 'titre', 'sous_titre', 'contenu', 'categorie', 'statut',
            'auteur', 'auteur_details', 'annee_academique', 'image_principale',
            'fichier_joint', 'est_une_alerte', 'est_epingle', 'date_publication',
            'date_expiration', 'vues', 'tags', 'tags_list', 'est_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at', 'vues']
    
    def validate(self, data):
        """Validation personnalisée."""
        # Si on publie, mettre automatiquement la date de publication
        if data.get('statut') == 'publie' and not data.get('date_publication'):
            from django.utils import timezone
            data['date_publication'] = timezone.now()
        
        return data


class ActualiteListSerializer(serializers.ModelSerializer):
    """Serializer simplifié pour les listes d'actualités."""
    
    auteur_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = Actualite
        fields = [
            'id', 'titre', 'sous_titre', 'categorie', 'statut', 'auteur_nom',
            'image_principale', 'est_une_alerte', 'est_epingle',
            'date_publication', 'vues', 'created_at'
        ]
    
    def get_auteur_nom(self, obj):
        """Retourne le nom complet de l'auteur."""
        if obj.auteur:
            return obj.auteur.get_full_name()
        return None


class InscriptionEvenementSerializer(serializers.ModelSerializer):
    """Serializer pour les inscriptions aux événements."""
    
    participant_details = UserSerializer(source='participant', read_only=True)
    evenement_details = EventListSerializer(source='evenement', read_only=True)
    
    class Meta:
        model = InscriptionEvenement
        fields = [
            'id', 'evenement', 'evenement_details', 'participant',
            'participant_details', 'statut', 'nombre_accompagnants',
            'commentaire', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def validate(self, data):
        """Validation personnalisée."""
        evenement = data.get('evenement')
        
        # Vérifier si l'événement requiert une inscription
        if not evenement.inscription_requise:
            raise serializers.ValidationError(
                "Cet événement ne requiert pas d'inscription."
            )
        
        # Vérifier si l'événement est passé
        if evenement.est_passe:
            raise serializers.ValidationError(
                "Impossible de s'inscrire à un événement passé."
            )
        
        # Vérifier si l'événement est annulé
        if evenement.statut == 'annule':
            raise serializers.ValidationError(
                "Impossible de s'inscrire à un événement annulé."
            )
        
        return data


class ActualitePubliqueSerializer(serializers.ModelSerializer):
    """Serializer pour la consultation publique des actualités (sans champs sensibles)."""
    
    auteur_nom = serializers.SerializerMethodField()
    tags_list = serializers.ListField(source='get_tags_list', read_only=True)
    
    class Meta:
        model = Actualite
        fields = [
            'id', 'titre', 'sous_titre', 'contenu', 'categorie',
            'auteur_nom', 'image_principale', 'fichier_joint',
            'est_une_alerte', 'date_publication', 'vues', 'tags_list'
        ]
    
    def get_auteur_nom(self, obj):
        """Retourne le nom complet de l'auteur."""
        if obj.auteur:
            return obj.auteur.get_full_name()
        return None


class EventPublicSerializer(serializers.ModelSerializer):
    """Serializer pour la consultation publique des événements (sans champs sensibles)."""
    
    organisateur_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'titre', 'description', 'type_evenement', 'date_debut',
            'date_fin', 'lieu', 'organisateur_nom', 'statut', 'image',
            'participants_attendus', 'inscription_requise'
        ]
    
    def get_organisateur_nom(self, obj):
        """Retourne le nom complet de l'organisateur."""
        if obj.organisateur:
            return obj.organisateur.get_full_name()
        return None
