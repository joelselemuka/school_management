"""
Service pour générer le Bilan comptable selon normes OHADA.

Le bilan présente la situation financière de l'école à une date donnée:
- Actif: Ce que possède l'école
- Passif: Ce que l'école doit

Structure OHADA:
ACTIF:
- Actif immobilisé (immobilisations)
- Actif circulant (stocks, créances, trésorerie)

PASSIF:
- Capitaux propres
- Dettes long terme
- Dettes court terme
"""

from django.db.models import Sum, Q, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from comptabilite.models import Account, TransactionLine


class BilanService:
    """Service pour générer le bilan comptable OHADA."""
    
    @staticmethod
    def generate_bilan(date_fin, annee_academique=None):
        """
        Génère le bilan comptable à une date donnée.
        
        Args:
            date_fin: Date de clôture du bilan
            annee_academique: Année académique (optionnel)
            
        Returns:
            dict: Bilan avec actif et passif
        """
        actif = BilanService._calculer_actif(date_fin)
        passif = BilanService._calculer_passif(date_fin)
        
        total_actif = sum(actif.values())
        total_passif = sum(passif.values())
        
        return {
            'date_bilan': date_fin,
            'actif': actif,
            'passif': passif,
            'total_actif': total_actif,
            'total_passif': total_passif,
            'equilibre': total_actif == total_passif,
            'ecart': total_actif - total_passif,
        }
    
    @staticmethod
    def _calculer_actif(date_fin):
        """Calcule les postes de l'actif."""
        actif = {}
        
        # ACTIF IMMOBILISÉ (Comptes 2x)
        actif['immobilisations_incorporelles'] = BilanService._solde_comptes(
            '20', '21', date_fin, type_compte='asset'
        )
        actif['immobilisations_corporelles'] = BilanService._solde_comptes(
            '22', '25', date_fin, type_compte='asset'
        )
        actif['immobilisations_financieres'] = BilanService._solde_comptes(
            '26', '27', date_fin, type_compte='asset'
        )
        
        actif['total_actif_immobilise'] = (
            actif['immobilisations_incorporelles'] +
            actif['immobilisations_corporelles'] +
            actif['immobilisations_financieres']
        )
        
        # ACTIF CIRCULANT
        actif['stocks'] = BilanService._solde_comptes(
            '30', '39', date_fin, type_compte='asset'
        )
        actif['creances_clients'] = BilanService._solde_comptes(
            '40', '41', date_fin, type_compte='asset'
        )
        actif['autres_creances'] = BilanService._solde_comptes(
            '42', '48', date_fin, type_compte='asset'
        )
        
        actif['total_actif_circulant_hors_tresorerie'] = (
            actif['stocks'] +
            actif['creances_clients'] +
            actif['autres_creances']
        )
        
        # TRÉSORERIE ACTIF
        actif['banques'] = BilanService._solde_comptes(
            '52', '53', date_fin, type_compte='asset'
        )
        actif['caisse'] = BilanService._solde_comptes(
            '57', '57', date_fin, type_compte='asset'
        )
        
        actif['total_tresorerie_actif'] = (
            actif['banques'] +
            actif['caisse']
        )
        
        actif['total_actif_circulant'] = (
            actif['total_actif_circulant_hors_tresorerie'] +
            actif['total_tresorerie_actif']
        )
        
        return actif
    
    @staticmethod
    def _calculer_passif(date_fin):
        """Calcule les postes du passif."""
        passif = {}
        
        # CAPITAUX PROPRES (Comptes 10)
        passif['capital'] = BilanService._solde_comptes(
            '101', '101', date_fin, type_compte='equity'
        )
        passif['reserves'] = BilanService._solde_comptes(
            '106', '108', date_fin, type_compte='equity'
        )
        passif['report_a_nouveau'] = BilanService._solde_comptes(
            '11', '11', date_fin, type_compte='equity'
        )
        passif['resultat_exercice'] = BilanService._calculer_resultat(date_fin)
        
        passif['total_capitaux_propres'] = (
            passif['capital'] +
            passif['reserves'] +
            passif['report_a_nouveau'] +
            passif['resultat_exercice']
        )
        
        # DETTES FINANCIÈRES (Comptes 16, 17)
        passif['emprunts_long_terme'] = BilanService._solde_comptes(
            '16', '17', date_fin, type_compte='liability'
        )
        
        # DETTES CIRCULANTES
        passif['fournisseurs'] = BilanService._solde_comptes(
            '40', '40', date_fin, type_compte='liability'
        )
        passif['dettes_fiscales'] = BilanService._solde_comptes(
            '44', '44', date_fin, type_compte='liability'
        )
        passif['dettes_sociales'] = BilanService._solde_comptes(
            '42', '43', date_fin, type_compte='liability'
        )
        passif['autres_dettes'] = BilanService._solde_comptes(
            '45', '48', date_fin, type_compte='liability'
        )
        
        passif['total_dettes_circulantes'] = (
            passif['fournisseurs'] +
            passif['dettes_fiscales'] +
            passif['dettes_sociales'] +
            passif['autres_dettes']
        )
        
        # TRÉSORERIE PASSIF
        passif['banques_decouvert'] = BilanService._solde_comptes(
            '52', '53', date_fin, type_compte='liability'
        )
        
        return passif
    
    @staticmethod
    def _solde_comptes(code_debut, code_fin, date_fin, type_compte):
        """
        Calcule le solde d'une plage de comptes.
        
        Args:
            code_debut: Code de début (ex: '20')
            code_fin: Code de fin (ex: '25')
            date_fin: Date de calcul
            type_compte: Type de compte (asset, liability, equity)
        """
        accounts = Account.objects.filter(
            code__gte=code_debut,
            code__lte=code_fin + 'ZZZZ',  # Pour inclure tous les sous-comptes
            type=type_compte
        )
        
        if not accounts.exists():
            return Decimal('0.00')
        
        # Calculer solde des lignes d'écriture
        lines = TransactionLine.objects.filter(
            account__in=accounts,
            transaction__date__lte=date_fin
        )
        
        total_debit = lines.aggregate(
            total=Coalesce(Sum('debit'), Decimal('0'), output_field=DecimalField())
        )['total']
        
        total_credit = lines.aggregate(
            total=Coalesce(Sum('credit'), Decimal('0'), output_field=DecimalField())
        )['total']
        
        # Pour actif: Débit - Crédit (solde débiteur)
        # Pour passif: Crédit - Débit (solde créditeur)
        if type_compte == 'asset':
            return total_debit - total_credit
        else:  # liability ou equity
            return total_credit - total_debit
    
    @staticmethod
    def _calculer_resultat(date_fin):
        """Calcule le résultat de l'exercice (Produits - Charges)."""
        from comptabilite.services.compte_resultat_service import CompteResultatService
        
        compte_resultat = CompteResultatService.generate_compte_resultat(
            date_debut=None,  # Début d'exercice
            date_fin=date_fin
        )
        
        return compte_resultat.get('resultat_net', Decimal('0.00'))
    
    @staticmethod
    def generate_bilan_compare(date_n, date_n_1):
        """
        Génère un bilan comparatif N / N-1.
        
        Args:
            date_n: Date bilan année N
            date_n_1: Date bilan année N-1
            
        Returns:
            dict: Bilan comparatif avec variations
        """
        bilan_n = BilanService.generate_bilan(date_n)
        bilan_n_1 = BilanService.generate_bilan(date_n_1)
        
        return {
            'annee_n': bilan_n,
            'annee_n_1': bilan_n_1,
            'variations': BilanService._calculer_variations(
                bilan_n['actif'],
                bilan_n_1['actif']
            )
        }
    
    @staticmethod
    def _calculer_variations(data_n, data_n_1):
        """Calcule les variations entre deux exercices."""
        variations = {}
        
        for key in data_n.keys():
            if key in data_n_1:
                valeur_n = data_n[key]
                valeur_n_1 = data_n_1[key]
                variation_absolue = valeur_n - valeur_n_1
                
                if valeur_n_1 != 0:
                    variation_pct = (variation_absolue / valeur_n_1) * 100
                else:
                    variation_pct = 0
                
                variations[key] = {
                    'absolue': variation_absolue,
                    'pourcentage': variation_pct
                }
        
        return variations
