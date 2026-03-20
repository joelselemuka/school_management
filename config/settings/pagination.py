"""
Configuration de la pagination pour DRF.
Fusionné dans REST_FRAMEWORK via 'from .pagination import *' dans base.py.
"""

# Injectée dans REST_FRAMEWORK par base.py après import
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# Tailles personnalisées par usage (référence applicative)
PAGINATION_SETTINGS = {
    'small': 10,
    'default': 20,
    'medium': 50,
    'large': 100,
    'max': 500,
}

