"""
Configuration Rate Limiting / Throttling pour sécurité DDoS.
Fusionné dans REST_FRAMEWORK via 'from .throttling import *' dans base.py.
"""

# ─── Mise à jour de REST_FRAMEWORK avec les throttles avancés ────────────────
# Ces clés étendent la config REST_FRAMEWORK définie dans base.py
_THROTTLE_CLASSES = [
    'rest_framework.throttling.AnonRateThrottle',
    'rest_framework.throttling.UserRateThrottle',
    'rest_framework.throttling.ScopedRateThrottle',
]

_THROTTLE_RATES = {
    # Utilisateurs non authentifiés
    'anon': '100/hour',

    # Utilisateurs authentifiés
    'user': '1000/hour',

    # Scopes spécifiques
    'auth': '10/minute',       # Login/logout
    'uploads': '50/hour',      # Upload fichiers
    'exports': '20/hour',      # Export rapports
    'notifications': '100/hour',  # Envoi notifications
}

# Injectée dans REST_FRAMEWORK par base.py après import
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': _THROTTLE_CLASSES,
    'DEFAULT_THROTTLE_RATES': _THROTTLE_RATES,
}

# Throttling personnalisé par rôle (référence applicative)
THROTTLE_RATES_BY_ROLE = {
    'ADMIN': '10000/hour',
    'STAFF': '5000/hour',
    'DIRECTOR': '5000/hour',
    'TEACHER': '2000/hour',
    'ACCOUNTANT': '2000/hour',
    'SECRETARY': '2000/hour',
    'PARENT': '500/hour',
    'STUDENT': '300/hour',
}
