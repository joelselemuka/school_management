"""
Configuration Celery pour les tâches asynchrones.

Ce fichier configure Celery pour:
- Envoi d'emails en arrière-plan
- Génération de bulletins/factures
- Notifications en lot
- Tâches planifiées (cron)
"""

import os
from celery import Celery
from celery.schedules import crontab

# Set default Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

# Create Celery app
app = Celery('api_v3')

# Load config from Django settings with 'CELERY_' prefix
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


# Configuration des tâches périodiques
app.conf.beat_schedule = {
    # Envoi quotidien des notifications
    'send-daily-notifications': {
        'task': 'communication.tasks.send_daily_notifications',
        'schedule': crontab(hour=8, minute=0),  # Tous les jours à 8h
    },
    
    # Génération automatique des bulletins
    'generate-bulletins-end-of-period': {
        'task': 'academics.tasks.generate_period_bulletins',
        'schedule': crontab(day_of_month='28', hour=20, minute=0),  # Le 28 à 20h
    },
    
    # Rappel des impayés
    'send-payment-reminders': {
        'task': 'finance.tasks.send_payment_reminders',
        'schedule': crontab(day_of_week='monday', hour=9, minute=0),  # Tous les lundis à 9h
    },
    
    # Nettoyage des sessions expirées
    'cleanup-expired-sessions': {
        'task': 'common.tasks.cleanup_expired_sessions',
        'schedule': crontab(hour=2, minute=0),  # Tous les jours à 2h du matin
    },
    
    # Backup automatique des données critiques
    'backup-critical-data': {
        'task': 'common.tasks.backup_critical_data',
        'schedule': crontab(hour=3, minute=0),  # Tous les jours à 3h du matin
    },
    
    # Application des pénalités
    'apply-penalties-every-night': {
        'task': 'finance.tasks.apply_penalties',
        'schedule': crontab(hour=23, minute=30),  # Tous les jours à 23h30
    },
}


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Tâche de debug pour tester Celery."""
    print(f'Request: {self.request!r}')
