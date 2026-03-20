"""
Service pour générer le Compte de Résultat selon normes OHADA.

Le compte de résultat présente les performances de l'école sur une période:
- Produits (revenus)
- Charges (dépenses)
- Résultat = Produits - Charges

Structure OHADA:
- Produits d'exploitation
- Charges d'exploitation
- Résultat d'exploitation
- Produits financiers
- Charges financières
- Résultat financier
- Résultat net
"""

from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
from decimal import Decimal
from comptabilite.models import Account, TransactionLine
from datetime import datetime


class CompteResultatService:
    """Service pour générer le compte de résultat OHADA."""
    
    @staticmethod
    def generate_compte_resultat(date_debut, date_fin, annee_academique=None):
        """
        Génère le compte de résultat pour une période.
        
        Args:
            date_debut: Date de début de période
            date_fin: Date de fin de période
            annee_academique: Année académique (optionnel)
            
        Returns:
            dict: Compte de résultat détaillé
        """
        if date_debut is None:
            # Prendre le début de l'année fiscale
            date_debut = datetime(date_fin.year, 1, 1).date()
        
        produits = CompteResultatService._calculer_produits(date_debut, date_fin)
        charges = CompteResultatService._calculer_charges(date_debut, date_fin)
        
        # Calculs intermédiaires
        total_produits_exploitation = sum([
            v for k, v in produits.items() 
            if k.startswith('produits_exploitation')
        ])
        
        total_charges_exploitation = sum([
            v for k, v in charges.items() 
            if k.startswith('charges_exploitation')
        ])
        
        resultat_exploitation = total_produits_exploitation - total_charges_exploitation
        
        total_produits_financiers = produits.get('produits_financiers', Decimal('0'))
        total_charges_financieres = charges.get('charges_financieres', Decimal('0'))
        
        resultat_financier = total_produits_financiers - total_charges_financieres
        
        resultat_net = resultat_exploitation + resultat_financier
        
        return {
            'periode': {
                'debut': date_debut,
                'fin': date_fin
            },
            'produits': produits,
            'charges': charges,
            'total_produits_exploitation': total_produits_exploitation,
            'total_charges_exploitation': total_charges_exploitation,
            'resultat_exploitation': resultat_exploitation,
            'total_produits_financiers': total_produits_financiers,
            'total_charges_financieres': total_charges_financieres,
            'resultat_financier': resultat_financier,
            'resultat_net': resultat_net,
            'rentabilite': (resultat_net / total_produits_exploitation * 100) 
                          if total_produits_exploitation > 0 else Decimal('0')
        }
    
    @staticmethod
    def _calculer_produits(date_debut, date_fin):
        """Calcule tous les postes de produits."""
        produits = {}
        
        # PRODUITS D'EXPLOITATION (Comptes 70-75)
        
        # 70 - Ventes de marchandises (non applicable pour école)
        produits['produits_exploitation_ventes'] = Decimal('0.00')
        
        # 70x - Frais de scolarité (principal produit pour une école)
        produits['produits_exploitation_scolarite'] = CompteResultatService._solde_comptes_periode(
            '701', '702', date_debut, date_fin, type_compte='income'
        )
        
        # 706 - Autres prestations de services (cantine, transport, etc.)
        produits['produits_exploitation_services'] = CompteResultatService._solde_comptes_periode(
            '706', '706', date_debut, date_fin, type_compte='income'
        )
        
        # 707 - Produits accessoires
        produits['produits_exploitation_accessoires'] = CompteResultatService._solde_comptes_periode(
            '707', '707', date_debut, date_fin, type_compte='income'
        )
        
        # 71 - Subventions d'exploitation
        produits['produits_exploitation_subventions'] = CompteResultatService._solde_comptes_periode(
            '71', '71', date_debut, date_fin, type_compte='income'
        )
        
        # 75 - Autres produits de gestion courante
        produits['produits_exploitation_autres'] = CompteResultatService._solde_comptes_periode(
            '75', '75', date_debut, date_fin, type_compte='income'
        )
        
        # PRODUITS FINANCIERS (Comptes 77)
        produits['produits_financiers'] = CompteResultatService._solde_comptes_periode(
            '77', '77', date_debut, date_fin, type_compte='income'
        )
        
        # PRODUITS EXCEPTIONNELS (Comptes 84)
        produits['produits_exceptionnels'] = CompteResultatService._solde_comptes_periode(
            '84', '84', date_debut, date_fin, type_compte='income'
        )
        
        return produits
    
    @staticmethod
    def _calculer_charges(date_debut, date_fin):
        """Calcule tous les postes de charges."""
        charges = {}
        
        # CHARGES D'EXPLOITATION
        
        # 60 - Achats de marchandises
        charges['charges_exploitation_achats'] = CompteResultatService._solde_comptes_periode(
            '60', '60', date_debut, date_fin, type_compte='expense'
        )
        
        # 61 - Transport
        charges['charges_exploitation_transport'] = CompteResultatService._solde_comptes_periode(
            '61', '61', date_debut, date_fin, type_compte='expense'
        )
        
        # 62 - Autres services extérieurs (loyer, entretien, etc.)
        charges['charges_exploitation_services'] = CompteResultatService._solde_comptes_periode(
            '62', '62', date_debut, date_fin, type_compte='expense'
        )
        
        # 63 - Autres services extérieurs (publicité, assurances, etc.)
        charges['charges_exploitation_autres_services'] = CompteResultatService._solde_comptes_periode(
            '63', '63', date_debut, date_fin, type_compte='expense'
        )
        
        # 64 - Impôts et taxes
        charges['charges_exploitation_impots'] = CompteResultatService._solde_comptes_periode(
            '64', '64', date_debut, date_fin, type_compte='expense'
        )
        
        # 66 - Charges de personnel (PRINCIPAL pour une école)
        charges['charges_exploitation_personnel'] = CompteResultatService._solde_comptes_periode(
            '66', '66', date_debut, date_fin, type_compte='expense'
        )
        
        # 68 - Dotations aux amortissements
        charges['charges_exploitation_amortissements'] = CompteResultatService._solde_comptes_periode(
            '68', '68', date_debut, date_fin, type_compte='expense'
        )
        
        # CHARGES FINANCIÈRES (Comptes 67)
        charges['charges_financieres'] = CompteResultatService._solde_comptes_periode(
            '67', '67', date_debut, date_fin, type_compte='expense'
        )
        
        # CHARGES EXCEPTIONNELLES (Comptes 85)
        charges['charges_exceptionnelles'] = CompteResultatService._solde_comptes_periode(
            '85', '85', date_debut, date_fin, type_compte='expense'
        )
        
        return charges
    
    @staticmethod
    def _solde_comptes_periode(code_debut, code_fin, date_debut, date_fin, type_compte):
        """
        Calcule le total des mouvements pour une plage de comptes sur une période.
        
        Args:
            code_debut: Code de début
            code_fin: Code de fin
            date_debut: Date de début
            date_fin: Date de fin
            type_compte: Type de compte (income ou expense)
        """
        accounts = Account.objects.filter(
            code__gte=code_debut,
            code__lte=code_fin + 'ZZZZ',
            type=type_compte
        )
        
        if not accounts.exists():
            return Decimal('0.00')
        
        lines = TransactionLine.objects.filter(
            account__in=accounts,
            transaction__date__gte=date_debut,
            transaction__date__lte=date_fin
        )
        
        total_debit = lines.aggregate(
            total=Coalesce(Sum('debit'), Decimal('0'), output_field=DecimalField())
        )['total']
        
        total_credit = lines.aggregate(
            total=Coalesce(Sum('credit'), Decimal('0'), output_field=DecimalField())
        )['total']
        
        # Pour income (produits): Crédit - Débit (solde créditeur)
        # Pour expense (charges): Débit - Crédit (solde débiteur)
        if type_compte == 'income':
            return total_credit - total_debit
        else:  # expense
            return total_debit - total_credit
    
    @staticmethod
    def generate_compte_resultat_compare(date_debut_n, date_fin_n, date_debut_n_1, date_fin_n_1):
        """
        Génère un compte de résultat comparatif N / N-1.
        
        Args:
            date_debut_n: Date début année N
            date_fin_n: Date fin année N
            date_debut_n_1: Date début année N-1
            date_fin_n_1: Date fin année N-1
            
        Returns:
            dict: Compte de résultat comparatif avec variations
        """
        cr_n = CompteResultatService.generate_compte_resultat(date_debut_n, date_fin_n)
        cr_n_1 = CompteResultatService.generate_compte_resultat(date_debut_n_1, date_fin_n_1)
        
        return {
            'annee_n': cr_n,
            'annee_n_1': cr_n_1,
            'variations': {
                'resultat_net': {
                    'absolue': cr_n['resultat_net'] - cr_n_1['resultat_net'],
                    'pourcentage': (
                        ((cr_n['resultat_net'] - cr_n_1['resultat_net']) / cr_n_1['resultat_net'] * 100)
                        if cr_n_1['resultat_net'] != 0 else Decimal('0')
                    )
                },
                'resultat_exploitation': {
                    'absolue': cr_n['resultat_exploitation'] - cr_n_1['resultat_exploitation'],
                    'pourcentage': (
                        ((cr_n['resultat_exploitation'] - cr_n_1['resultat_exploitation']) / cr_n_1['resultat_exploitation'] * 100)
                        if cr_n_1['resultat_exploitation'] != 0 else Decimal('0')
                    )
                }
            }
        }
    
    @staticmethod
    def generer_ratios_performance(compte_resultat):
        """
        Génère les ratios de performance à partir du compte de résultat.
        
        Args:
            compte_resultat: dict du compte de résultat
            
        Returns:
            dict: Ratios de performance
        """
        total_produits = compte_resultat['total_produits_exploitation']
        charges_personnel = compte_resultat['charges'].get('charges_exploitation_personnel', Decimal('0'))
        resultat_net = compte_resultat['resultat_net']
        
        return {
            'taux_marge_nette': (
                (resultat_net / total_produits * 100) 
                if total_produits > 0 else Decimal('0')
            ),
            'taux_charges_personnel': (
                (charges_personnel / total_produits * 100)
                if total_produits > 0 else Decimal('0')
            ),
            'taux_marge_exploitation': (
                (compte_resultat['resultat_exploitation'] / total_produits * 100)
                if total_produits > 0 else Decimal('0')
            )
        }
