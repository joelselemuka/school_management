"""
Configuration django-axes pour la protection contre les attaques brute force.
"""

from datetime import timedelta

# ─── Django Axes ──────────────────────────────────────────────────────────────

# Nombre de tentatives échouées avant le blocage
AXES_FAILURE_LIMIT = 5

# Durée du blocage (30 minutes)
AXES_COOLOFF_TIME = timedelta(minutes=30)

# Réinitialiser le compteur après un login réussi
AXES_RESET_ON_SUCCESS = True

# Ne compter que les échecs par utilisateur (pas par IP + utilisateur)
#AXES_ONLY_USER_FAILURES = True

# Utiliser le cache pour le stockage (plus performant que la DB)
AXES_HANDLER = 'axes.handlers.cache.AxesCacheHandler'

# Message de blocage personnalisé
AXES_LOCKOUT_PARAMETERS = ['username','ip_address']

# Logging
AXES_VERBOSE = True
