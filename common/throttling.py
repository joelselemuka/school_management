"""
Classes de throttling personnalisées basées sur les rôles.
"""

from rest_framework.throttling import UserRateThrottle
from django.conf import settings


class RoleBasedThrottle(UserRateThrottle):
    """
    Throttling basé sur le rôle de l'utilisateur.
    
    Les admins ont des limites plus élevées que les étudiants.
    """
    
    def get_rate(self):
        """Retourne le rate selon le rôle de l'utilisateur."""
        if not self.request.user.is_authenticated:
            return '100/hour'  # Anonymes
        
        # Récupérer le rôle de l'utilisateur
        user = self.request.user
        role = getattr(user, 'role', 'STUDENT')
        
        # Retourner le rate selon le rôle
        rates = getattr(settings, 'THROTTLE_RATES_BY_ROLE', {})
        return rates.get(role, '500/hour')
    
    def get_cache_key(self, request, view):
        """Cache key unique par utilisateur."""
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            ident = self.get_ident(request)
        
        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class AuthThrottle(UserRateThrottle):
    """Throttling pour authentification (login/logout)."""
    scope = 'auth'
    rate = '10/minute'  # Max 10 tentatives login/minute


class UploadThrottle(UserRateThrottle):
    """Throttling pour upload de fichiers."""
    scope = 'uploads'
    rate = '50/hour'


class ExportThrottle(UserRateThrottle):
    """Throttling pour export de rapports."""
    scope = 'exports'
    rate = '20/hour'


class NotificationThrottle(UserRateThrottle):
    """Throttling pour envoi de notifications."""
    scope = 'notifications'
    rate = '100/hour'


class BurstRateThrottle(UserRateThrottle):
    """
    Throttling pour burst requests (pics de trafic).
    Permet des pics courts mais limite sur période longue.
    """
    rate = '50/minute'  # 50 requêtes par minute max
