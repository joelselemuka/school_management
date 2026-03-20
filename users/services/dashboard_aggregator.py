from typing import Dict, Any
import logging
from common.role_services import RoleService
from core.models import AnneeAcademique

logger = logging.getLogger(__name__)

class DashboardAggregatorService:
    def __init__(self, user):
        self.user = user
        self.annee_active = AnneeAcademique.objects.filter(actif=True).first()

    def get_dashboard_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "user": {
                "id": self.user.id,
                "full_name": self.user.full_name,
                "email": self.user.email,
                "roles": []
            }
        }
        
        try:
            if RoleService.is_eleve(self.user):
                data["user"]["roles"].append("eleve")
                data["eleve"] = self._build_eleve_dashboard(self.user.eleve_profile)
                
            if RoleService.is_parent(self.user):
                data["user"]["roles"].append("parent")
                data["parent"] = self._build_parent_dashboard(self.user.parent_profile)
                
            if RoleService.is_personnel(self.user):
                data["user"]["roles"].append("personnel")
                prof = self.user.personnel_profile
                data["user"]["roles"].append(prof.fonction)
                
                data["personnel"] = self._build_personnel_dashboard(prof)
                
                if prof.fonction == "enseignant":
                    data["enseignant"] = self._build_teacher_dashboard(prof)
                if prof.fonction == "chauffeur":
                    data["chauffeur"] = self._build_driver_dashboard(prof)
                if prof.fonction == "bibliothecaire":
                    data["bibliotheque"] = self._build_librarian_dashboard(prof)
        except Exception as e:
            logger.error(f"Error building dashboard for user {self.user.id}: {str(e)}")
            data["error"] = "Une erreur partielle est survenue lors de la collecte des donnees."

        return data

    def _build_eleve_dashboard(self, eleve) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        try:
            from admission.models import Inscription
            inscription = Inscription.objects.filter(eleve=eleve, annee_academique=self.annee_active, actif=True).first()
            if inscription and inscription.classe:
                result['classe'] = inscription.classe.nom
                
                # Cours
                try:
                    from academics.models import Cours
                    result['cours'] = list(Cours.objects.filter(classe=inscription.classe).values('id', 'nom', 'code'))
                except Exception: pass
        except Exception: pass
        
        # Notes & Bulletins
        try:
            from academics.models import Note, Bulletin
            result['notes'] = list(Note.objects.filter(eleve=eleve, evaluation__annee_academique=self.annee_active).values('id', 'valeur', 'evaluation__nom', 'evaluation__bareme', 'date_saisie')[:10])
            result['bulletins'] = list(Bulletin.objects.filter(inscription__eleve=eleve).values('id', 'periode__nom', 'moyenne', 'mention'))
        except Exception: pass
        
        # Finances
        try:
            from finance.models import CompteEleve, DetteEleve, Paiement
            compte = CompteEleve.objects.filter(eleve=eleve, annee_academique=self.annee_active).first()
            if compte:
                result['finance_solde'] = str(compte.solde)
                result['finance_total_du'] = str(compte.total_du)
            
            result['dettes'] = list(DetteEleve.objects.filter(eleve=eleve, statut__in=['IMPAYE', 'PARTIEL']).values('frais__nom', 'montant_du', 'statut'))
            result['paiements'] = list(Paiement.objects.filter(eleve=eleve).values('reference', 'montant', 'mode', 'status').order_by('-id')[:5])
        except Exception: pass
            
        # Transport
        try:
            from transport.models import AffectationEleveTransport
            transport = AffectationEleveTransport.objects.filter(eleve=eleve, annee_academique=self.annee_active, actif=True).first()
            if transport:
                result['transport'] = {
                    "itineraire": transport.itineraire.nom,
                    "montee": transport.arret_montee.arret.nom if transport.arret_montee else None,
                    "descente": transport.arret_descente.arret.nom if transport.arret_descente else None
                }
        except Exception: pass
        
        # Bibliotheque
        try:
            from bibliotheque.models import Emprunt
            emprunts = Emprunt.objects.filter(emprunteur=self.user, statut__in=['EN_COURS', 'EN_RETARD'])
            result['livres_empruntes'] = list(emprunts.values('exemplaire__livre__titre', 'date_emprunt', 'date_retour_prevue', 'statut'))
        except Exception: pass
            
        return result

    def _build_parent_dashboard(self, parent) -> Dict[str, Any]:
        result: Dict[str, Any] = {"enfants": []}
        try:
            from users.models import ParentEleve
            enfants_links = ParentEleve.objects.filter(parent=parent)
            
            for link in enfants_links:
                enfant_data = self._build_eleve_dashboard(link.eleve)
                enfant_data['eleve_id'] = link.eleve.id
                enfant_data['nom_complet'] = str(link.eleve)
                enfant_data['relation'] = link.relation
                result["enfants"].append(enfant_data)
        except Exception: pass
        return result

    def _build_personnel_dashboard(self, prof) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        # Paie & Presence
        try:
            from paie.models import ContratEmploye, SommairePaiePersonnel
            contrat = ContratEmploye.objects.filter(personnel=prof, est_actif=True).first()
            if contrat:
                result['contrat'] = {"type": contrat.type_contrat, "salaire_base": str(contrat.salaire_base)}
                
            sommaires = SommairePaiePersonnel.objects.filter(personnel=prof).order_by('-annee', '-mois')[:3]
            result['dernieres_paies'] = list(sommaires.values('mois', 'annee', 'total_jours_presents'))
        except Exception: pass
        
        try:
            from attendance.models import PresencePersonnel
            presences = PresencePersonnel.objects.filter(personnel=prof).order_by('-date')[:5]
            result['presences_recentes'] = list(presences.values('date', 'statut', 'heure_arrivee'))
        except Exception: pass
        
        return result

    def _build_teacher_dashboard(self, prof) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        try:
            from academics.models import Cours
            cours = Cours.objects.filter(enseignant=prof)
            result['mes_cours'] = list(cours.values('nom', 'classe__nom'))
        except Exception: pass
        return result

    def _build_driver_dashboard(self, prof) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        try:
            from transport.models import AffectationChauffeur, AffectationEleveTransport
            affectations = AffectationChauffeur.objects.filter(chauffeur=prof, actif=True)
            result['mes_bus'] = list(affectations.values('bus__numero', 'itineraire__nom'))
            
            itineraires = [a.itineraire for a in affectations]
            eleves = AffectationEleveTransport.objects.filter(itineraire__in=itineraires, actif=True)
            result['eleves_a_transporter'] = list(eleves.values('eleve__nom', 'eleve__prenom', 'arret_montee__arret__nom', 'arret_descente__arret__nom'))
        except Exception: pass
        return result

    def _build_librarian_dashboard(self, prof) -> Dict[str, Any]:
        result: Dict[str, Any] = {}
        try:
            from bibliotheque.models import Emprunt, Livre
            result['total_livres'] = Livre.objects.count()
            result['emprunts_en_cours'] = Emprunt.objects.filter(statut='EN_COURS').count()
            result['emprunts_en_retard'] = Emprunt.objects.filter(statut='EN_RETARD').count()
        except Exception: pass
        return result
