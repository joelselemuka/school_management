from rest_framework import serializers
from bibliotheque.models import Livre, Exemplaire, Emprunt, PaiementAmende, Inventaire, LigneInventaire

class LivreSerializer(serializers.ModelSerializer):
    exemplaires_disponibles = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Livre
        fields = [
            'id', 'titre', 'auteur', 'isbn', 'categorie', 'langue', 
            'date_publication', 'description', 'photo', 'exemplaires_disponibles', 'actif'
        ]

class ExemplaireSerializer(serializers.ModelSerializer):
    livre_details = LivreSerializer(source='livre', read_only=True)
    
    class Meta:
        model = Exemplaire
        fields = [
            'id', 'livre', 'livre_details', 'code_barre', 'etat', 
            'est_disponible', 'date_acquisition', 'prix_acquisition', 'remarque', 'actif'
        ]

class EmpruntSerializer(serializers.ModelSerializer):
    exemplaire_details = ExemplaireSerializer(source='exemplaire', read_only=True)
    emprunteur_nom = serializers.CharField(source='emprunteur.get_full_name', read_only=True)
    est_en_retard = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Emprunt
        fields = [
            'id', 'exemplaire', 'exemplaire_details', 'emprunteur', 'emprunteur_nom',
            'date_emprunt', 'date_retour_prevue', 'date_retour_effective', 'statut',
            'enregistre_par', 'retour_enregistre_par', 'remarque_emprunt', 'remarque_retour',
            'est_en_retard'
        ]
        read_only_fields = ['date_emprunt', 'date_retour_effective', 'statut', 'enregistre_par', 'retour_enregistre_par']

class PaiementAmendeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaiementAmende
        fields = '__all__'
        read_only_fields = ['reference', 'date_paiement', 'percu_par']

class LigneInventaireSerializer(serializers.ModelSerializer):
    class Meta:
        model = LigneInventaire
        fields = '__all__'

class InventaireSerializer(serializers.ModelSerializer):
    lignes = LigneInventaireSerializer(many=True, read_only=True)
    responsable_nom = serializers.CharField(source='responsable.get_full_name', read_only=True)
    
    class Meta:
        model = Inventaire
        fields = [
            'id', 'nom', 'date_debut', 'date_cloture', 'en_cours', 
            'responsable', 'responsable_nom', 'observations', 'lignes'
        ]
        read_only_fields = ['date_debut', 'date_cloture', 'responsable']
