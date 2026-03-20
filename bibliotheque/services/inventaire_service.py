from django.utils import timezone
from bibliotheque.models import Inventaire, Exemplaire

class InventaireService:
    @staticmethod
    def create_inventaire(validated_data, user):
        return Inventaire.objects.create(
            responsable=user,
            en_cours=True,
            **validated_data
        )

    @staticmethod
    def update_inventaire(inventaire, validated_data):
        for attr, value in validated_data.items():
            setattr(inventaire, attr, value)
        inventaire.save()
        return inventaire

    @staticmethod
    def cloturer_inventaire(inventaire):
        inventaire.en_cours = False
        inventaire.date_cloture = timezone.now().date()
        inventaire.save(update_fields=["en_cours", "date_cloture"])
        return inventaire

    @staticmethod
    def get_all():
        return Inventaire.objects.all()

    @staticmethod
    def generer_rapport(inventaire):
        """
        Génère un rapport détaillé de l'inventaire croisant les exemplaires existants
        et ceux pointés lors de cet inventaire.
        """
        tous_exemplaires = Exemplaire.objects.filter(actif=True)
        total_attendu = tous_exemplaires.count()
        
        lignes = inventaire.lignes.select_related('exemplaire', 'exemplaire__livre')
        scannes_ids = lignes.values_list('exemplaire_id', flat=True)
        
        # Ce qui a été formellement vu
        presents = lignes.filter(est_present=True)
        total_presents = presents.count()
        
        # Ce qui a été formellement déclaré absent
        declarés_absents = lignes.filter(est_present=False)
        
        # Ce qui n'a même pas été scanné/pointé (oubli ou disparition totale)
        non_scannes = tous_exemplaires.exclude(id__in=scannes_ids)
        
        # Détails des anomalies
        livres_manquants_details = []
        for l in declarés_absents:
            livres_manquants_details.append({
                "code_barre": l.exemplaire.code_barre,
                "titre": l.exemplaire.livre.titre,
                "raison": "Déclaré absent lors du pointage"
            })
            
        for ext in non_scannes:
            livres_manquants_details.append({
                "code_barre": ext.code_barre,
                "titre": ext.livre.titre,
                "raison": "Non scanné / Introuvable"
            })

        # Changements d'état constatés (ex: de NEUF à USE)
        degradations = []
        for l in presents:
            if l.statut_constate and l.statut_constate != l.exemplaire.etat:
                degradations.append({
                    "code_barre": l.exemplaire.code_barre,
                    "titre": l.exemplaire.livre.titre,
                    "ancien_etat": l.exemplaire.etat,
                    "nouvel_etat": l.statut_constate
                })

        return {
            "inventaire_id": inventaire.id,
            "nom": inventaire.nom,
            "date_debut": inventaire.date_debut,
            "date_cloture": inventaire.date_cloture,
            "statut": "Clôturé" if not inventaire.en_cours else "En cours",
            "statistiques": {
                "total_attendu_en_base": total_attendu,
                "total_retrouves": total_presents,
                "total_manquants": len(livres_manquants_details)
            },
            "anomalies": {
                "livres_manquants": livres_manquants_details,
                "degradations_constatees": degradations
            }
        }

