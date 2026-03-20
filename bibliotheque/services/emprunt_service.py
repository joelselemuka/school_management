import logging
from django.utils import timezone
from datetime import timedelta
from bibliotheque.models import Emprunt
from core.models import Ecole

logger = logging.getLogger(__name__)

class EmpruntService:
    @staticmethod
    def _envoyer_notification(user, message):
        """
        Placeholder log. Idéalement lié au module communication de base.
        """
        logger.info(f"NOTIFICATION to {user}: {message}")

    @staticmethod
    def create_emprunt(validated_data, user):
        exemplaire = validated_data.get('exemplaire')
        
        emprunt = Emprunt.objects.create(
            enregistre_par=user,
            statut="EN_COURS",
            **validated_data
        )
        exemplaire.est_disponible = False
        exemplaire.save(update_fields=["est_disponible"])
        return emprunt

    @staticmethod
    def retourner_livre(emprunt, user, data):
        emprunt.statut = "RETOURNE"
        emprunt.date_retour_effective = timezone.now().date()
        emprunt.retour_enregistre_par = user
        emprunt.remarque_retour = data.get("remarque", "")
        
        nouvel_etat = data.get("etat", None)
        if nouvel_etat:
            emprunt.exemplaire.etat = nouvel_etat
            
        emprunt.exemplaire.est_disponible = True
        emprunt.exemplaire.save(update_fields=["est_disponible", "etat"])
        emprunt.save()
        return emprunt

    @staticmethod
    def prolonger_emprunt(emprunt, nouvelle_date):
        emprunt.date_retour_prevue = nouvelle_date
        emprunt.save(update_fields=["date_retour_prevue"])
        return emprunt

    @staticmethod
    def verifier_retards_et_penalites():
        """
        Logique métier de calcul des pénalités basé sur core_ecole.
        Scrutateur exécuté journalièrement.
        """
        aujourd_hui = timezone.now().date()
        try:
            ecole = Ecole.get_configuration()
            jours_tolerance = ecole.biblio_jours_avant_penalite
            montant_base = ecole.biblio_montant_penalite
            type_penalite = ecole.biblio_type_penalite
        except Exception:
            logger.warning("Configuration Ecole absente, impossible d'appliquer les règles de bibliothèque.")
            return
            
        emprunts = Emprunt.objects.filter(statut__in=["EN_COURS", "EN_RETARD"])
        
        for e in emprunts:
            # 1. Rappel 2 jours avant
            if e.statut == "EN_COURS" and e.date_retour_prevue == (aujourd_hui + timedelta(days=2)):
                msg = f"Rappel préventif: Le délai du livre '{e.exemplaire.livre.titre}' expire dans 2 jours."
                EmpruntService._envoyer_notification(e.emprunteur, msg)
                
            # 2. Traitement Retard
            if aujourd_hui > e.date_retour_prevue:
                jours_retard = (aujourd_hui - e.date_retour_prevue).days
                
                if jours_retard > jours_tolerance:
                    penalite = 0
                    if type_penalite == "FIXE":
                        penalite = montant_base
                    elif type_penalite == "PAR_JOUR":
                        jours_facturables = jours_retard - jours_tolerance
                        penalite = montant_base * jours_facturables
                    
                    montant_a_jour = (e.montant_penalite != penalite)
                    changement_statut = (e.statut != "EN_RETARD")
                    
                    e.statut = "EN_RETARD"
                    e.montant_penalite = penalite
                    
                    if montant_a_jour or changement_statut:
                        e.save(update_fields=["statut", "montant_penalite"])
                        msg = f"Alerte Pénalité Bibliothèque: {penalite} appliqués pour '{e.exemplaire.livre.titre}' suite à un retard de {jours_retard} jour(s)."
                        EmpruntService._envoyer_notification(e.emprunteur, msg)
