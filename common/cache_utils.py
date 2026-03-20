"""
Utilitaires de cache pour l'application.
Utilise Redis pour le cache distribué.
"""

from django.core.cache import cache
from django.conf import settings
from functools import wraps
import hashlib
import json


def generate_cache_key(prefix, *args, **kwargs):
    """
    Génère une clé de cache unique basée sur les arguments.
    
    Args:
        prefix: Préfixe pour la clé (ex: 'bulletin', 'stats_classe')
        *args, **kwargs: Arguments pour générer une clé unique
    
    Returns:
        str: Clé de cache unique
    """
    # Créer une chaîne unique avec les arguments
    key_data = {
        'args': args,
        'kwargs': kwargs
    }
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"{prefix}:{key_hash}"


def cache_result(timeout=300, key_prefix='default'):
    """
    Décorateur pour mettre en cache le résultat d'une fonction.
    
    Args:
        timeout: Durée du cache en secondes (défaut: 5 minutes)
        key_prefix: Préfixe pour la clé de cache
    
    Usage:
        @cache_result(timeout=600, key_prefix='bulletin')
        def get_bulletin(eleve_id, trimestre_id):
            # code ici
            return bulletin
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Générer la clé de cache
            cache_key = generate_cache_key(key_prefix, *args, **kwargs)
            
            # Essayer de récupérer depuis le cache
            result = cache.get(cache_key)
            
            if result is not None:
                return result
            
            # Si pas en cache, exécuter la fonction
            result = func(*args, **kwargs)
            
            # Mettre en cache le résultat
            cache.set(cache_key, result, timeout)
            
            return result
        
        return wrapper
    return decorator


def invalidate_cache(key_prefix, *args, **kwargs):
    """
    Invalide une clé de cache spécifique.
    
    Args:
        key_prefix: Préfixe de la clé
        *args, **kwargs: Arguments pour générer la clé
    """
    cache_key = generate_cache_key(key_prefix, *args, **kwargs)
    cache.delete(cache_key)


def invalidate_cache_pattern(pattern):
    """
    Invalide toutes les clés correspondant à un pattern.
    
    Args:
        pattern: Pattern de clé (ex: 'bulletin:*', 'stats_classe:*')
    
    Note: Nécessite Redis
    """
    try:
        from django.core.cache.backends.redis import RedisCache
        from django_redis import get_redis_connection
        
        # Si on utilise Redis
        if isinstance(cache, RedisCache) or hasattr(cache, '_cache'):
            conn = get_redis_connection("default")
            keys = conn.keys(f"{pattern}")
            if keys:
                conn.delete(*keys)
    except Exception as e:
        # Si erreur, logger mais ne pas crasher
        print(f"Erreur invalidation cache pattern: {e}")


class CacheManager:
    """
    Gestionnaire centralisé du cache.
    
    Usage:
        from common.cache_utils import CacheManager
        
        # Mettre en cache
        CacheManager.set('bulletin', bulletin_data, eleve_id=1, trimestre=1)
        
        # Récupérer du cache
        data = CacheManager.get('bulletin', eleve_id=1, trimestre=1)
        
        # Invalider
        CacheManager.invalidate('bulletin', eleve_id=1, trimestre=1)
        CacheManager.invalidate_pattern('bulletin:*')
    """
    
    # Durées de cache par défaut (en secondes)
    TIMEOUTS = {
        'bulletin': 3600,        # 1 heure - changent peu
        'notes': 1800,           # 30 minutes - changent modérément
        'stats_classe': 900,     # 15 minutes
        'stats_eleve': 900,      # 15 minutes
        'paiements': 600,        # 10 minutes
        'factures': 1800,        # 30 minutes
        'bilan': 3600,           # 1 heure
        'compte_resultat': 3600, # 1 heure
        'bilan_compare': 3600,
        'compte_resultat_compare': 3600,
        'trial_balance': 600,
        'general_journal': 600,
        'general_ledger': 600,
        'income_statement': 600,
        'cash_flow_summary': 600,
        'daily_cash_journal': 300,
        'actualites': 300,       # 5 minutes
        'evenements': 600,       # 10 minutes
        'classes_list': 300,
        'cours_list': 300,
        'notes_list': 300,
        'evaluations_list': 300,
        'affectations_list': 300,
        'bulletins_list': 300,
        'admission_applications_list': 300,
        'inscriptions_list': 300,
        'frais_list': 300,
        'paiements_list': 300,
        'dettes_list': 300,
        'factures_list': 300,
        'comptes_list': 300,
        'salaires_list': 300,
        'default': 300,          # 5 minutes par défaut
    }
    
    @classmethod
    def get(cls, prefix, *args, **kwargs):
        """Récupérer du cache."""
        cache_key = generate_cache_key(prefix, *args, **kwargs)
        return cache.get(cache_key)
    
    @classmethod
    def set(cls, prefix, value, *args, timeout=None, **kwargs):
        """Mettre en cache."""
        cache_key = generate_cache_key(prefix, *args, **kwargs)
        
        # Utiliser le timeout spécifique ou celui par défaut
        if timeout is None:
            timeout = cls.TIMEOUTS.get(prefix, cls.TIMEOUTS['default'])
        
        cache.set(cache_key, value, timeout)
        return cache_key
    
    @classmethod
    def invalidate(cls, prefix, *args, **kwargs):
        """Invalider une clé spécifique."""
        invalidate_cache(prefix, *args, **kwargs)
    
    @classmethod
    def invalidate_pattern(cls, pattern):
        """Invalider toutes les clés d'un pattern."""
        invalidate_cache_pattern(pattern)
    
    @classmethod
    def get_or_set(cls, prefix, callback, *args, timeout=None, **kwargs):
        """
        Récupérer du cache ou exécuter callback et mettre en cache.
        
        Args:
            prefix: Préfixe de clé
            callback: Fonction à exécuter si pas en cache
            timeout: Durée du cache
        
        Returns:
            Résultat du cache ou de callback
        """
        # Essayer de récupérer
        result = cls.get(prefix, *args, **kwargs)
        
        if result is not None:
            return result
        
        # Exécuter callback et mettre en cache
        result = callback()
        cls.set(prefix, result, *args, timeout=timeout, **kwargs)
        
        return result


def invalidate_comptabilite_reports_cache():
    """
    Invalide les caches des rapports comptables.
    """
    prefixes = [
        "trial_balance",
        "general_journal",
        "general_ledger",
        "income_statement",
        "cash_flow_summary",
        "daily_cash_journal",
        "bilan",
        "bilan_compare",
        "compte_resultat",
        "compte_resultat_compare",
    ]
    for prefix in prefixes:
        CacheManager.invalidate_pattern(f"{prefix}:*")


# Décorateurs spécialisés pour cas courants

def cache_bulletin(timeout=3600):
    """Décorateur pour mettre en cache les bulletins."""
    return cache_result(timeout=timeout, key_prefix='bulletin')


def cache_stats(timeout=900):
    """Décorateur pour mettre en cache les statistiques."""
    return cache_result(timeout=timeout, key_prefix='stats')


def cache_financial_data(timeout=1800):
    """Décorateur pour mettre en cache les données financières."""
    return cache_result(timeout=timeout, key_prefix='financial')


def cache_comptabilite(timeout=3600):
    """Décorateur pour mettre en cache les données comptables."""
    return cache_result(timeout=timeout, key_prefix='comptabilite')


# Fonctions d'invalidation spécialisées

def invalidate_bulletin_cache(eleve_id=None, trimestre_id=None):
    """
    Invalide le cache des bulletins.
    
    Args:
        eleve_id: Si spécifié, invalide seulement pour cet élève
        trimestre_id: Si spécifié, invalide seulement pour ce trimestre
    """
    if eleve_id and trimestre_id:
        CacheManager.invalidate('bulletin', eleve_id=eleve_id, trimestre_id=trimestre_id)
    elif eleve_id:
        CacheManager.invalidate_pattern(f'bulletin:*eleve_id*{eleve_id}*')
    else:
        CacheManager.invalidate_pattern('bulletin:*')


def invalidate_stats_cache(classe_id=None):
    """
    Invalide le cache des statistiques.
    
    Args:
        classe_id: Si spécifié, invalide seulement pour cette classe
    """
    if classe_id:
        CacheManager.invalidate_pattern(f'stats:*classe_id*{classe_id}*')
    else:
        CacheManager.invalidate_pattern('stats:*')


def invalidate_financial_cache(eleve_id=None):
    """
    Invalide le cache financier.
    
    Args:
        eleve_id: Si spécifié, invalide seulement pour cet élève
    """
    if eleve_id:
        CacheManager.invalidate_pattern(f'financial:*eleve_id*{eleve_id}*')
    else:
        CacheManager.invalidate_pattern('financial:*')

