
from django.db.models import Sum, Count, Q
from django.utils import timezone

from comptabilite.models import Expense
from finance.models import DetteEleve, Paiement, Frais, Facture


class FinanceService:
    """Service principal pour les opérations financières complexes."""
    
    @staticmethod
    def rapprochement_compte(eleve_id, annee_id):
        """
        Génère un rapport de rapprochement de compte pour un élève.
        
        Args:
            eleve_id: ID de l'élève
            annee_id: ID de l'année académique
            
        Returns:
            dict: Rapport avec détails des frais, paiements et solde
        """
        from users.models import Eleve
        from core.models import AnneeAcademique
        
        eleve = Eleve.objects.get(id=eleve_id)
        annee = AnneeAcademique.objects.get(id=annee_id)
        
        # Récupérer tous les frais de l'élève pour cette année
        frais = Frais.objects.filter(
            classe=eleve.classe_actuelle,
            annee_academique=annee
        )
        
        # Récupérer tous les paiements
        paiements = Paiement.objects.filter(
            eleve=eleve,
            created_at__year=annee.date_debut.year
        )
        
        # Récupérer les dettes
        dettes = DetteEleve.objects.filter(
            eleve=eleve,
            frais__annee_academique=annee
        )
        
        # Calculs
        total_frais = sum(f.montant for f in frais)
        total_paye = paiements.filter(statut='CONFIRMED').aggregate(
            total=Sum('montant')
        )['total'] or 0
        total_dette = dettes.exclude(statut='PAYE').aggregate(
            total=Sum('montant_restant')
        )['total'] or 0
        
        return {
            'eleve': {
                'id': eleve.id,
                'nom_complet': f"{eleve.nom} {eleve.postnom} {eleve.prenom}",
                'matricule': eleve.matricule,
                'classe': eleve.classe_actuelle.nom if eleve.classe_actuelle else None
            },
            'annee_academique': {
                'id': annee.id,
                'annee': annee.annee,
                'est_active': annee.actif
            },
            'frais': [
                {
                    'id': f.id,
                    'nom': f.nom,
                    'montant': float(f.montant),
                    'obligatoire': f.obligatoire
                } for f in frais
            ],
            'paiements': [
                {
                    'id': p.id,
                    'montant': float(p.montant),
                    'date': p.created_at.isoformat(),
                    'mode': p.mode_paiement,
                    'statut': p.statut
                } for p in paiements
            ],
            'dettes': [
                {
                    'id': d.id,
                    'frais': d.frais.nom,
                    'montant_total': float(d.montant_total),
                    'montant_paye': float(d.montant_paye),
                    'montant_restant': float(d.montant_restant),
                    'statut': d.statut
                } for d in dettes
            ],
            'resume': {
                'total_frais': float(total_frais),
                'total_paye': float(total_paye),
                'total_dette': float(total_dette),
                'solde': float(total_paye - total_frais)
            },
            'date_generation': timezone.now().isoformat()
        }
    
    @staticmethod
    def generate_global_report(annee_id):
        """
        Génère un rapport financier global pour une année académique.
        
        Args:
            annee_id: ID de l'année académique
            
        Returns:
            dict: Rapport global avec statistiques
        """
        from core.models import AnneeAcademique
        from users.models import Eleve
        
        annee = AnneeAcademique.objects.get(id=annee_id)
        
        # Statistiques des paiements
        paiements = Paiement.objects.filter(
            created_at__year=annee.date_debut.year
        )
        
        total_encaisse = paiements.filter(statut='CONFIRMED').aggregate(
            total=Sum('montant')
        )['total'] or 0
        
        paiements_en_attente = paiements.filter(statut='PENDING').aggregate(
            total=Sum('montant')
        )['total'] or 0
        
        # Statistiques des dettes
        dettes = DetteEleve.objects.filter(
            frais__annee_academique=annee
        )
        
        total_dettes = dettes.exclude(statut='PAYE').aggregate(
            total=Sum('montant_restant')
        )['total'] or 0
        
        # Statistiques par mode de paiement
        paiements_par_mode = paiements.filter(statut='CONFIRMED').values('mode_paiement').annotate(
            total=Sum('montant'),
            count=Count('id')
        )
        
        # Élèves avec dettes
        eleves_avec_dettes = dettes.exclude(statut='PAYE').values('eleve').distinct().count()
        
        return {
            'annee_academique': {
                'id': annee.id,
                'annee': annee.annee,
                'est_active': annee.actif
            },
            'statistiques_paiements': {
                'total_encaisse': float(total_encaisse),
                'paiements_en_attente': float(paiements_en_attente),
                'nombre_paiements': paiements.filter(statut='CONFIRMED').count(),
                'paiements_par_mode': [
                    {
                        'mode': p['mode_paiement'],
                        'total': float(p['total']),
                        'nombre': p['count']
                    } for p in paiements_par_mode
                ]
            },
            'statistiques_dettes': {
                'total_dettes': float(total_dettes),
                'nombre_eleves_avec_dettes': eleves_avec_dettes,
                'taux_recouvrement': float((total_encaisse / (total_encaisse + total_dettes) * 100) if (total_encaisse + total_dettes) > 0 else 0)
            },
            'date_generation': timezone.now().isoformat()
        }
    
    @staticmethod
    def generate_class_report(classe_id, annee_id):
        """
        Génère un rapport financier pour une classe.
        
        Args:
            classe_id: ID de la classe
            annee_id: ID de l'année académique
            
        Returns:
            dict: Rapport financier de la classe
        """
        from academics.models import Classe
        from core.models import AnneeAcademique
        from users.models import Eleve
        
        classe = Classe.objects.get(id=classe_id)
        annee = AnneeAcademique.objects.get(id=annee_id)
        
        # Récupérer les élèves de la classe
        eleves = Eleve.objects.filter(classe_actuelle=classe)
        
        # Frais de la classe
        frais = Frais.objects.filter(
            classe=classe,
            annee_academique=annee
        )
        
        total_frais_attendus = sum(f.montant for f in frais) * eleves.count()
        
        # Paiements des élèves
        paiements = Paiement.objects.filter(
            eleve__in=eleves,
            created_at__year=annee.date_debut.year,
            statut='CONFIRMED'
        )
        
        total_paye = paiements.aggregate(total=Sum('montant'))['total'] or 0
        
        # Dettes par élève
        dettes = DetteEleve.objects.filter(
            eleve__in=eleves,
            frais__annee_academique=annee
        ).exclude(statut='PAYE')
        
        total_dettes = dettes.aggregate(total=Sum('montant_restant'))['total'] or 0
        
        # Détails par élève
        eleves_details = []
        for eleve in eleves:
            eleve_paiements = paiements.filter(eleve=eleve).aggregate(
                total=Sum('montant')
            )['total'] or 0
            
            eleve_dettes = dettes.filter(eleve=eleve).aggregate(
                total=Sum('montant_restant')
            )['total'] or 0
            
            eleves_details.append({
                'eleve': {
                    'id': eleve.id,
                    'nom_complet': f"{eleve.nom} {eleve.postnom} {eleve.prenom}",
                    'matricule': eleve.matricule
                },
                'total_paye': float(eleve_paiements),
                'total_dette': float(eleve_dettes),
                'statut': 'A jour' if eleve_dettes == 0 else 'En dette'
            })
        
        return {
            'classe': {
                'id': classe.id,
                'nom': classe.nom,
                'effectif': eleves.count()
            },
            'annee_academique': {
                'id': annee.id,
                'annee': annee.annee
            },
            'frais_classe': [
                {
                    'id': f.id,
                    'nom': f.nom,
                    'montant': float(f.montant),
                    'obligatoire': f.obligatoire
                } for f in frais
            ],
            'resume_financier': {
                'total_frais_attendus': float(total_frais_attendus),
                'total_paye': float(total_paye),
                'total_dettes': float(total_dettes),
                'taux_recouvrement': float((total_paye / total_frais_attendus * 100) if total_frais_attendus > 0 else 0)
            },
            'eleves': eleves_details,
            'date_generation': timezone.now().isoformat()
        }


class FinanceGuardService:

    @staticmethod
    def has_unpaid_required_fees(eleve):
        return DetteEleve.objects.filter(
            eleve=eleve,
            frais__obligatoire=True
        ).exclude(statut="PAYE").exists()


class FinanceAnalyticsService:

    @staticmethod
    def total_encaisse(start, end):
        return (
            Paiement.objects
            .filter(
                statut="CONFIRMED",
                created_at__range=(start, end)
            )
            .aggregate(total=Sum("montant"))["total"] or 0
        )

    @staticmethod
    def total_depense(start, end):
        expense_total = (
            Expense.objects
            .filter(
                statut="APPROVED",
                date__range=(start, end)
            )
            .aggregate(total=Sum("amount"))["total"] or 0
        )

        from paie.models import PaiementSalaire
        salaire_total = (
            PaiementSalaire.objects
            .filter(
                statut="CONFIRMED",
                created_at__range=(start, end)
            )
            .aggregate(total=Sum("montant"))["total"] or 0
        )

        return expense_total + salaire_total
