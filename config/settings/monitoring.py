"""
Configuration Monitoring & Observabilité (Sentry, Logging).
"""

import os
import logging

# Sentry Configuration (Error Tracking)
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
SENTRY_ENVIRONMENT = os.getenv('SENTRY_ENVIRONMENT', 'development')
SENTRY_TRACES_SAMPLE_RATE = float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.1'))

if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[
            DjangoIntegration(),
            CeleryIntegration(),
            RedisIntegration(),
        ],
        environment=SENTRY_ENVIRONMENT,
        traces_sample_rate=SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,  # Ne pas envoyer PII par défaut
        
        # Performance monitoring
        profiles_sample_rate=0.1,
        
        # Release tracking
        release=os.getenv('GIT_COMMIT', 'unknown'),
        
        # Before send hook (filtrer données sensibles)
        before_send=lambda event, hint: event,
    )

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
        }
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/django_errors.log',
            'maxBytes': 1024 * 1024 * 15,  # 15MB
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'celery_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/celery.log',
            'maxBytes': 1024 * 1024 * 15,
            'backupCount': 10,
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['require_debug_false'],
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'sentry_sdk.integrations.logging.EventHandler',
            'filters': ['require_debug_false'],
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['error_file', 'mail_admins', 'sentry'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['error_file', 'mail_admins'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery': {
            'handlers': ['celery_file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'academics': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if os.getenv('DEBUG') == 'True' else 'INFO',
            'propagate': False,
        },
        'finance': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if os.getenv('DEBUG') == 'True' else 'INFO',
            'propagate': False,
        },
        'communication': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG' if os.getenv('DEBUG') == 'True' else 'INFO',
            'propagate': False,
        },
        'performance': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'INFO',
    },
}

# Health Check URLs
HEALTH_CHECK_URLS = {
    'health': '/health/',
    'readiness': '/health/ready/',
    'liveness': '/health/alive/',
    'detailed': '/health/detailed/',
}

# Monitoring Alertes
MONITORING_ALERTS = {
    'email': os.getenv('MONITORING_EMAIL', 'admin@school.com'),
    'slack_webhook': os.getenv('SLACK_WEBHOOK_URL', ''),
    'sms_number': os.getenv('ALERT_SMS_NUMBER', ''),
}

# Performance Thresholds
PERFORMANCE_THRESHOLDS = {
    'api_response_time': 200,  # ms
    'database_query_time': 100,  # ms
    'cache_hit_rate': 80,  # %
    'error_rate': 1,  # %
}

# Request profiling (logs slow requests with DB query counts)
REQUEST_PROFILING_ENABLED = os.getenv('REQUEST_PROFILING_ENABLED', 'False') == 'True'
REQUEST_PROFILING_THRESHOLD_MS = int(os.getenv('REQUEST_PROFILING_THRESHOLD_MS', '250'))
