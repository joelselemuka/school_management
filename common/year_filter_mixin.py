"""
Mixin et utilitaires pour filtrer les données par année académique.
Permet de filtrer automatiquement par année active ou par une année spécifique.
"""

from django.db.models import Q
from rest_framework import status
from rest_framework.response import Response
from core.models import AnneeAcademique


class AcademicYearFilterMixin:
    """
    Mixin pour filtrer automatiquement les QuerySets par année académique.
    
    Usage dans un ViewSet:
        class ClasseViewSet(AcademicYearFilterMixin, viewsets.ModelViewSet):
            queryset = Classe.objects.all()
            year_filter_field = 'annee_academique'  # Nom du champ FK
            ...
    
    Comportement:
    - Par défaut, filtre sur l'année académique ACTIVE
    - Si query param `annee_id=X` fourni, filtre sur cette année
    - Si query param `all_years=true`, pas de filtrage (toutes années)
    """
    
    # Nom du champ pour filtrer (à surcharger si nécessaire)
    year_filter_field = 'annee_academique'
    
    # Permettre de désactiver le filtrage par année
    enable_year_filter = True
    
    def get_queryset(self):
        """
        Filtre le queryset par année académique.
        """
        queryset = super().get_queryset()
        
        # Si le filtrage est désactivé pour ce ViewSet
        if not self.enable_year_filter:
            return queryset
        
        # Vérifier si le modèle a le champ année académique
        if not hasattr(queryset.model, self.year_filter_field):
            return queryset
        
        # Query params
        request = self.request
        annee_id = request.query_params.get('annee_id', None)
        all_years = request.query_params.get('all_years', 'false').lower() == 'true'
        
        # Si all_years=true, retourner tout
        if all_years:
            # Vérifier que l'utilisateur a le droit
            if request.user.is_staff or request.user.role in ['super_admin', 'director']:
                return queryset
            # Sinon, continuer avec filtrage normal
        
        # Si année spécifique demandée
        if annee_id:
            try:
                annee = AnneeAcademique.objects.get(id=annee_id)
                filter_kwargs = {self.year_filter_field: annee}
                return queryset.filter(**filter_kwargs)
            except AnneeAcademique.DoesNotExist:
                # Année invalide, retourner queryset vide
                return queryset.none()
        
        # Par défaut, filtrer sur l'année ACTIVE
        try:
            annee_active = AnneeAcademique.objects.filter(est_active=True).first()
            if annee_active:
                filter_kwargs = {self.year_filter_field: annee_active}
                return queryset.filter(**filter_kwargs)
        except Exception:
            pass
        
        # Si pas d'année active, retourner tout
        return queryset
    
    def get_academic_year(self):
        """
        Retourne l'année académique à utiliser pour les opérations.
        
        Returns:
            AnneeAcademique: L'année académique active ou spécifiée
        """
        request = self.request
        annee_id = request.query_params.get('annee_id', None)
        
        # Si année spécifique demandée
        if annee_id:
            try:
                return AnneeAcademique.objects.get(id=annee_id)
            except AnneeAcademique.DoesNotExist:
                return None
        
        # Sinon, retourner l'année active
        return AnneeAcademique.objects.filter(est_active=True).first()


class MultipleYearFilterMixin(AcademicYearFilterMixin):
    """
    Mixin pour modèles avec plusieurs relations à des années académiques.
    
    Exemple: InscriptionEleve a une FK vers Eleve, qui a une FK vers AnneeAcademique
    
    Usage:
        class InscriptionViewSet(MultipleYearFilterMixin, viewsets.ModelViewSet):
            year_filter_field = 'eleve__annee_academique'
            ...
    """
    pass


def get_active_academic_year():
    """
    Récupère l'année académique active.
    
    Returns:
        AnneeAcademique ou None
    """
    return AnneeAcademique.objects.filter(est_active=True).first()


def get_academic_year_from_request(request):
    """
    Récupère l'année académique depuis la requête.
    
    Args:
        request: Request Django/DRF
    
    Returns:
        AnneeAcademique ou None
    
    Priorité:
    1. Query param `annee_id`
    2. Cookie `annee_academique_id`
    3. Année active
    """
    # 1. Query param
    annee_id = request.query_params.get('annee_id') if hasattr(request, 'query_params') else request.GET.get('annee_id')
    
    if annee_id:
        try:
            return AnneeAcademique.objects.get(id=annee_id)
        except (AnneeAcademique.DoesNotExist, ValueError):
            pass
    
    # 2. Cookie
    annee_id_cookie = request.COOKIES.get('annee_academique_id')
    if annee_id_cookie:
        try:
            return AnneeAcademique.objects.get(id=annee_id_cookie)
        except (AnneeAcademique.DoesNotExist, ValueError):
            pass
    
    # 3. Année active par défaut
    return get_active_academic_year()


def filter_by_academic_year(queryset, year_filter_field='annee_academique', annee=None):
    """
    Filtre un queryset par année académique.
    
    Args:
        queryset: QuerySet à filtrer
        year_filter_field: Nom du champ pour filtrer
        annee: Instance AnneeAcademique (si None, utilise l'année active)
    
    Returns:
        QuerySet filtré
    """
    if annee is None:
        annee = get_active_academic_year()
    
    if annee is None:
        return queryset
    
    filter_kwargs = {year_filter_field: annee}
    return queryset.filter(**filter_kwargs)


class AcademicYearQueryParamMixin:
    """
    Mixin pour ajouter automatiquement le paramètre d'année académique
    dans la documentation Swagger/OpenAPI.
    """
    
    def get_serializer_context(self):
        """Ajoute l'année académique au contexte du serializer."""
        context = super().get_serializer_context()
        context['academic_year'] = get_academic_year_from_request(self.request)
        return context


# Décorateur pour les fonctions qui nécessitent une année académique

def require_academic_year(func):
    """
    Décorateur pour s'assurer qu'une année académique est disponible.
    
    Usage:
        @require_academic_year
        def my_view(request):
            annee = get_academic_year_from_request(request)
            ...
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(request, *args, **kwargs):
        annee = get_academic_year_from_request(request)
        if annee is None:
            from rest_framework.response import Response
            from rest_framework import status
            return Response(
                {'error': 'Aucune année académique active trouvée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return func(request, *args, **kwargs)
    
    return wrapper


# Fonction pour obtenir les années académiques disponibles

def get_available_academic_years(user=None):
    """
    Retourne les années académiques accessibles.
    
    Args:
        user: Utilisateur (optionnel)
    
    Returns:
        QuerySet d'AnneeAcademique
    """
    queryset = AnneeAcademique.objects.all().order_by('-date_debut')
    
    # Si utilisateur non-staff, retourner seulement années actives/récentes
    if user and not user.is_staff:
        # Retourner l'année active + 2 dernières années
        queryset = queryset.filter(
            Q(est_active=True) |
            Q(date_fin__year__gte=2024)  # Années depuis 2024
        )
    
    return queryset


# Classe helper pour les services

class AcademicYearServiceMixin:
    """
    Mixin pour les services qui manipulent des données par année académique.
    
    Usage:
        class BulletinService(AcademicYearServiceMixin):
            def generer_bulletin(self, eleve, trimestre, annee=None):
                annee = self.get_year(annee)
                ...
    """
    
    def get_year(self, annee=None):
        """
        Retourne l'année académique à utiliser.
        
        Args:
            annee: AnneeAcademique ou None
        
        Returns:
            AnneeAcademique
        """
        if annee is not None:
            return annee
        
        # Utiliser l'année active
        annee_active = get_active_academic_year()
        if annee_active is None:
            raise ValueError("Aucune année académique active")
        
        return annee_active
    
    def filter_by_year(self, queryset, field='annee_academique', annee=None):
        """
        Filtre un queryset par année.
        
        Args:
            queryset: QuerySet à filtrer
            field: Nom du champ
            annee: AnneeAcademique ou None
        
        Returns:
            QuerySet filtré
        """
        annee = self.get_year(annee)
        return filter_by_academic_year(queryset, field, annee)
