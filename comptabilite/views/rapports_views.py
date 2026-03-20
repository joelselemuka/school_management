"""
ViewSets pour les rapports comptables OHADA.
"""

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from django.utils.dateparse import parse_date
from datetime import datetime, timedelta

from common.permissions import IsAccountant, IsAdminUser, IsDirector
from common.cache_utils import CacheManager
from comptabilite.services.bilan_service import BilanService
from comptabilite.services.compte_resultat_service import CompteResultatService
from comptabilite.plan_comptable_ohada import (
    PLAN_COMPTABLE_OHADA_ECOLE,
    get_plan_comptable_par_type,
    creer_comptes_depuis_plan
)


class RapportsComptablesViewSet(viewsets.ViewSet):
    """
    ViewSet pour les rapports comptables OHADA.
    
    Endpoints:
    - GET /rapports/bilan/ - Génère le bilan comptable
    - GET /rapports/compte-resultat/ - Génère le compte de résultat
    - GET /rapports/bilan-compare/ - Bilan comparatif N/N-1
    - GET /rapports/compte-resultat-compare/ - CR comparatif N/N-1
    - GET /rapports/ratios/ - Ratios de performance
    """
    
    permission_classes = [IsAuthenticated, IsAdminUser | IsAccountant | IsDirector]
    
    @action(detail=False, methods=['get'], url_path='bilan')
    def bilan(self, request):
        """
        GET /api/v1/comptabilite/rapports/bilan/?date_fin=2026-06-30
        
        Génère le bilan comptable à une date donnée.
        
        Query params:
            - date_fin: Date de clôture (requis)
            - annee_academique: ID année académique (optionnel)
        """
        date_fin_str = request.query_params.get('date_fin')
        
        if not date_fin_str:
            return Response(
                {'error': 'Le paramètre date_fin est requis (format: YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_fin = parse_date(date_fin_str)
            if not date_fin:
                raise ValueError("Format de date invalide")
        except:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        annee_academique_id = request.query_params.get('annee_academique')

        try:
            cache_key_args = {
                "user_id": getattr(request.user, "id", None),
                "date_fin": date_fin_str,
                "annee_academique": annee_academique_id,
            }
            cached = CacheManager.get("bilan", **cache_key_args)
            if cached is not None:
                return Response(cached)

            bilan = BilanService.generate_bilan(date_fin, annee_academique_id)
            
            payload = {
                'success': True,
                'data': bilan,
                'message': 'Bilan généré avec succès'
            }
            CacheManager.set("bilan", payload, **cache_key_args)
            return Response(payload)
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la génération du bilan: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='compte-resultat')
    def compte_resultat(self, request):
        """
        GET /api/v1/comptabilite/rapports/compte-resultat/?date_debut=2025-09-01&date_fin=2026-06-30
        
        Génère le compte de résultat pour une période.
        
        Query params:
            - date_debut: Date de début (optionnel, défaut: début année fiscale)
            - date_fin: Date de fin (requis)
            - annee_academique: ID année académique (optionnel)
        """
        date_fin_str = request.query_params.get('date_fin')
        date_debut_str = request.query_params.get('date_debut')
        
        if not date_fin_str:
            return Response(
                {'error': 'Le paramètre date_fin est requis (format: YYYY-MM-DD)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_fin = parse_date(date_fin_str)
            date_debut = parse_date(date_debut_str) if date_debut_str else None
            
            if not date_fin:
                raise ValueError("Format de date invalide")
                
        except:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        annee_academique_id = request.query_params.get('annee_academique')

        try:
            cache_key_args = {
                "user_id": getattr(request.user, "id", None),
                "date_debut": date_debut_str,
                "date_fin": date_fin_str,
                "annee_academique": annee_academique_id,
            }
            cached = CacheManager.get("compte_resultat", **cache_key_args)
            if cached is not None:
                return Response(cached)

            compte_resultat = CompteResultatService.generate_compte_resultat(
                date_debut, date_fin, annee_academique_id
            )
            
            payload = {
                'success': True,
                'data': compte_resultat,
                'message': 'Compte de résultat généré avec succès'
            }
            CacheManager.set("compte_resultat", payload, **cache_key_args)
            return Response(payload)
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la génération du compte de résultat: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='bilan-compare')
    def bilan_compare(self, request):
        """
        GET /api/v1/comptabilite/rapports/bilan-compare/?date_n=2026-06-30&date_n_1=2025-06-30
        
        Génère un bilan comparatif entre deux exercices.
        
        Query params:
            - date_n: Date bilan année N (requis)
            - date_n_1: Date bilan année N-1 (requis)
        """
        date_n_str = request.query_params.get('date_n')
        date_n_1_str = request.query_params.get('date_n_1')
        
        if not date_n_str or not date_n_1_str:
            return Response(
                {'error': 'Les paramètres date_n et date_n_1 sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_n = parse_date(date_n_str)
            date_n_1 = parse_date(date_n_1_str)
            
            if not date_n or not date_n_1:
                raise ValueError("Format de date invalide")
                
        except:
            return Response(
                {'error': 'Format de date invalide. Utilisez YYYY-MM-DD'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cache_key_args = {
                "user_id": getattr(request.user, "id", None),
                "date_n": date_n_str,
                "date_n_1": date_n_1_str,
            }
            cached = CacheManager.get("bilan_compare", **cache_key_args)
            if cached is not None:
                return Response(cached)

            bilan_compare = BilanService.generate_bilan_compare(date_n, date_n_1)
            
            payload = {
                'success': True,
                'data': bilan_compare,
                'message': 'Bilan comparatif généré avec succès'
            }
            CacheManager.set("bilan_compare", payload, **cache_key_args)
            return Response(payload)
            
        except Exception as e:
            return Response(
                {'error': f'Erreur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='compte-resultat-compare')
    def compte_resultat_compare(self, request):
        """
        GET /api/v1/comptabilite/rapports/compte-resultat-compare/
            ?date_debut_n=2025-09-01&date_fin_n=2026-06-30
            &date_debut_n_1=2024-09-01&date_fin_n_1=2025-06-30
        
        Génère un compte de résultat comparatif.
        """
        date_debut_n_str = request.query_params.get('date_debut_n')
        date_fin_n_str = request.query_params.get('date_fin_n')
        date_debut_n_1_str = request.query_params.get('date_debut_n_1')
        date_fin_n_1_str = request.query_params.get('date_fin_n_1')
        
        if not all([date_debut_n_str, date_fin_n_str, date_debut_n_1_str, date_fin_n_1_str]):
            return Response(
                {'error': 'Tous les paramètres de dates sont requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_debut_n = parse_date(date_debut_n_str)
            date_fin_n = parse_date(date_fin_n_str)
            date_debut_n_1 = parse_date(date_debut_n_1_str)
            date_fin_n_1 = parse_date(date_fin_n_1_str)
            
        except:
            return Response(
                {'error': 'Format de date invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cache_key_args = {
                "user_id": getattr(request.user, "id", None),
                "date_debut_n": date_debut_n_str,
                "date_fin_n": date_fin_n_str,
                "date_debut_n_1": date_debut_n_1_str,
                "date_fin_n_1": date_fin_n_1_str,
            }
            cached = CacheManager.get("compte_resultat_compare", **cache_key_args)
            if cached is not None:
                return Response(cached)

            cr_compare = CompteResultatService.generate_compte_resultat_compare(
                date_debut_n, date_fin_n,
                date_debut_n_1, date_fin_n_1
            )
            
            payload = {
                'success': True,
                'data': cr_compare,
                'message': 'Compte de résultat comparatif généré avec succès'
            }
            CacheManager.set("compte_resultat_compare", payload, **cache_key_args)
            return Response(payload)
            
        except Exception as e:
            return Response(
                {'error': f'Erreur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='ratios')
    def ratios(self, request):
        """
        GET /api/v1/comptabilite/rapports/ratios/?date_debut=2025-09-01&date_fin=2026-06-30
        
        Calcule les ratios de performance financière.
        """
        date_fin_str = request.query_params.get('date_fin')
        date_debut_str = request.query_params.get('date_debut')
        
        if not date_fin_str:
            return Response(
                {'error': 'Le paramètre date_fin est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            date_fin = parse_date(date_fin_str)
            date_debut = parse_date(date_debut_str) if date_debut_str else None
            
            # Générer compte de résultat
            compte_resultat = CompteResultatService.generate_compte_resultat(
                date_debut, date_fin
            )
            
            # Calculer ratios
            ratios = CompteResultatService.generer_ratios_performance(compte_resultat)
            
            return Response({
                'success': True,
                'data': {
                    'ratios': ratios,
                    'periode': compte_resultat['periode'],
                    'resultat_net': compte_resultat['resultat_net']
                },
                'message': 'Ratios calculés avec succès'
            })
            
        except Exception as e:
            return Response(
                {'error': f'Erreur: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlanComptableViewSet(viewsets.ViewSet):
    """
    ViewSet pour le plan comptable OHADA.
    
    Endpoints:
    - GET /plan-comptable/ - Liste complète du plan comptable
    - GET /plan-comptable/par-type/ - Comptes par type
    - POST /plan-comptable/initialiser/ - Initialise le plan comptable en DB
    """
    
    permission_classes = [IsAuthenticated, IsAdminUser | IsAccountant]
    
    def list(self, request):
        """
        GET /api/v1/comptabilite/plan-comptable/
        
        Retourne le plan comptable complet.
        """
        comptes = PLAN_COMPTABLE_OHADA_ECOLE
        paginator = PageNumberPagination()
        paginator.page_size = 20
        page = paginator.paginate_queryset(comptes, request)
        if page is not None:
            return Response({
                'success': True,
                'data': {
                    'plan_comptable': page,
                    'total_comptes': len(comptes),
                    'next': paginator.get_next_link(),
                    'previous': paginator.get_previous_link(),
                }
            })

        return Response({
            'success': True,
            'data': {
                'plan_comptable': comptes,
                'total_comptes': len(comptes)
            }
        })
    
    @action(detail=False, methods=['get'], url_path='par-type')
    def par_type(self, request):
        """
        GET /api/v1/comptabilite/plan-comptable/par-type/?type=income
        
        Retourne les comptes d'un type spécifique.
        
        Query params:
            - type: asset, liability, equity, income, expense
        """
        type_compte = request.query_params.get('type')
        
        if not type_compte:
            return Response(
                {'error': 'Le paramètre type est requis (asset, liability, equity, income, expense)'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valides = ['asset', 'liability', 'equity', 'income', 'expense']
        if type_compte not in valides:
            return Response(
                {'error': f'Type invalide. Types valides: {", ".join(valides)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        comptes = get_plan_comptable_par_type(type_compte)
        
        return Response({
            'success': True,
            'data': {
                'type': type_compte,
                'comptes': comptes,
                'total': len(comptes)
            }
        })
    
    @action(detail=False, methods=['post'], url_path='initialiser')
    def initialiser(self, request):
        """
        POST /api/v1/comptabilite/plan-comptable/initialiser/
        
        Initialise le plan comptable OHADA dans la base de données.
        Crée tous les comptes du plan.
        
        ATTENTION: À exécuter une seule fois lors de l'installation!
        """
        # Vérifier permission Admin uniquement
        if not request.user.role == 'ADMIN':
            return Response(
                {'error': 'Seul un administrateur peut initialiser le plan comptable'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            result = creer_comptes_depuis_plan()
            
            return Response({
                'success': True,
                'data': result,
                'message': f"Plan comptable initialisé: {result['created']} créés, {result['updated']} mis à jour"
            })
            
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de l\'initialisation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
