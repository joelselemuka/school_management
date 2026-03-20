"""
Configuration drf-spectacular pour la documentation Swagger/OpenAPI.
"""

# Spectacular (Swagger/OpenAPI) Settings
SPECTACULAR_SETTINGS = {
    'TITLE': 'School Management System API',
    'DESCRIPTION': '''
    API complète pour la gestion d'une institution scolaire.
    
    ## Fonctionnalités
    
    - **Gestion utilisateurs**: Authentification, rôles, permissions
    - **Gestion académique**: Classes, cours, évaluations, notes, bulletins
    - **Gestion finances**: Frais, paiements, dettes, factures
    - **Gestion présences**: Horaires, séances, présences
    - **Communication**: Notifications, chat en temps réel
    - **Admissions**: Inscriptions en ligne et au bureau
    
    ## Authentification
    
    L'API utilise JWT (JSON Web Tokens) pour l'authentification.
    
    1. Obtenir un token: `POST /api/v1/auth/token/`
    2. Utiliser le token dans le header: `Authorization: Bearer <token>`
    3. Rafraîchir le token: `POST /api/v1/auth/token/refresh/`
    
    ## Permissions
    
    L'API implémente un système RBAC (Role-Based Access Control) avec 9 rôles:
    - ADMIN, STAFF, DIRECTOR (accès complet)
    - TEACHER (ses classes)
    - ACCOUNTANT (données financières)
    - SECRETARY (données administratives)
    - PARENT (données de ses enfants)
    - STUDENT (ses propres données)
    
    ## Pagination
    
    Toutes les listes sont paginées:
    - `?page=1` - Numéro de page
    - `?page_size=20` - Nombre d'éléments par page
    
    ## Filtrage & Recherche
    
    - `?search=<terme>` - Recherche textuelle
    - `?ordering=<champ>` - Tri (ajouter `-` pour DESC)
    - Filtres spécifiques à chaque endpoint
    
    ## Codes de Réponse
    
    - `200` - OK
    - `201` - Créé
    - `400` - Erreur de validation
    - `401` - Non authentifié
    - `403` - Permission refusée
    - `404` - Non trouvé
    - `500` - Erreur serveur
    ''',
    'VERSION': '3.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    
    # Swagger UI settings
    'SWAGGER_UI_SETTINGS': {
        'deepLinking': True,
        'persistAuthorization': True,
        'displayOperationId': True,
        'filter': True,
        'tryItOutEnabled': True,
    },
    
    # Security schemes
    'SECURITY': [
        {
            'Bearer': {
                'type': 'http',
                'scheme': 'bearer',
                'bearerFormat': 'JWT',
            }
        }
    ],
    
    # Tags pour organiser les endpoints
    'TAGS': [
        {'name': 'Authentication', 'description': 'Authentification et tokens'},
        {'name': 'Users', 'description': 'Gestion des utilisateurs'},
        {'name': 'Core', 'description': 'Configuration (école, années, périodes)'},
        {'name': 'Academics', 'description': 'Gestion académique (cours, notes, bulletins)'},
        {'name': 'Admission', 'description': 'Admissions et inscriptions'},
        {'name': 'Attendance', 'description': 'Présences et horaires'},
        {'name': 'Finance', 'description': 'Gestion financière'},
        {'name': 'Communication', 'description': 'Notifications et chat'},
        {'name': 'Audit', 'description': 'Logs d\'audit et traçabilité'},
    ],
    
    # Component settings
    'COMPONENT_SPLIT_REQUEST': True,
    'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    
    # Schema settings
    'SCHEMA_PATH_PREFIX': '/api/v1/',
    'SCHEMA_PATH_PREFIX_TRIM': True,
    'SCHEMA_COERCE_PATH_PK': True,
    
    # Enum handling
    'ENUM_NAME_OVERRIDES': {
        'StatusEnum': 'common.models.StatusChoices',
        'RoleEnum': 'users.models.RoleChoices',
    },
    
    # Postprocessing
    'POSTPROCESSING_HOOKS': [
        'drf_spectacular.hooks.postprocess_schema_enums',
    ],
    
    # Extensions
    'EXTENSIONS_INFO': {
        'x-logo': {
            'url': '/static/logo.png',
            'altText': 'School Management System',
        }
    },
}

# OpenAPI 3.0 Settings
OPENAPI_VERSION = '3.0.3'
