"""
Tâches Celery pour maintenance système.
"""

from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
from datetime import timedelta
import subprocess
import os
import logging

logger = logging.getLogger(__name__)


@shared_task
def cleanup_expired_sessions():
    """
    Tâche planifiée: Nettoie les sessions expirées.
    
    Exécutée chaque jour à 2h du matin via Celery Beat.
    """
    try:
        call_command('clearsessions')
        logger.info("Sessions expirées nettoyées avec succès")
        return "Sessions expirées nettoyées"
    except Exception as e:
        logger.error(f"Erreur nettoyage sessions: {e}")
        raise


@shared_task
def backup_critical_data():
    """
    Tâche planifiée: Backup automatique des données critiques.
    
    Exécutée chaque jour à 3h du matin via Celery Beat.
    """
    try:
        # Exécuter le script de backup
        script_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'scripts',
            'backup_database.sh'
        )
        
        if os.path.exists(script_path):
            result = subprocess.run(
                ['bash', script_path],
                capture_output=True,
                text=True,
                timeout=3600  # 1 heure max
            )
            
            if result.returncode == 0:
                logger.info("Backup automatique réussi")
                return f"Backup réussi: {result.stdout}"
            else:
                logger.error(f"Erreur backup: {result.stderr}")
                raise Exception(f"Backup failed: {result.stderr}")
        else:
            logger.warning(f"Script backup introuvable: {script_path}")
            return "Script backup non trouvé"
            
    except subprocess.TimeoutExpired:
        logger.error("Timeout du backup (>1h)")
        raise
    except Exception as e:
        logger.error(f"Erreur backup: {e}")
        raise


@shared_task
def cleanup_old_audit_logs():
    """
    Nettoie les anciens logs d'audit (> 1 an).
    
    Exécutée une fois par mois.
    """
    from common.models import AuditLog
    
    one_year_ago = timezone.now() - timedelta(days=365)
    
    deleted_count, _ = AuditLog.objects.filter(
        timestamp__lt=one_year_ago
    ).delete()
    
    logger.info(f"{deleted_count} logs d'audit supprimés")
    return f"{deleted_count} logs d'audit supprimés"


@shared_task
def cleanup_old_documents():
    """
    Archive les anciens documents (> 3 ans).
    """
    from common.models import Document
    
    three_years_ago = timezone.now() - timedelta(days=365*3)
    
    # Au lieu de supprimer, on peut archiver
    documents = Document.objects.filter(
        uploaded_at__lt=three_years_ago,
        is_archived=False
    )
    
    count = documents.update(is_archived=True)
    
    logger.info(f"{count} documents archivés")
    return f"{count} documents archivés"


@shared_task
def generate_daily_statistics():
    """
    Génère les statistiques quotidiennes.
    
    Exécutée chaque jour à 23h.
    """
    from core.models import AnneeAcademique
    
    # Récupérer l'année active
    annee = AnneeAcademique.objects.filter(actif=True).first()
    if not annee:
        return "Aucune année académique active"
    
    stats = {
        'date': timezone.now().date().isoformat(),
        'annee': annee.nom,
        'inscriptions': annee.inscriptions.count(),
        'presences_today': 0,  # TODO: Calculer
        'paiements_today': 0,  # TODO: Calculer
    }
    
    # Sauvegarder les stats (dans un modèle ou cache)
    from django.core.cache import cache
    cache_key = f'daily_stats_{timezone.now().date()}'
    cache.set(cache_key, stats, timeout=86400*7)  # 7 jours
    
    logger.info(f"Statistiques quotidiennes générées: {stats}")
    return stats


@shared_task
def send_system_health_report():
    """
    Envoie un rapport de santé système aux admins.
    
    Exécutée chaque lundi à 9h.
    """
    from django.core.mail import send_mail
    from django.conf import settings
    import psutil
    
    # Collecter les métriques
    health = {
        'memory': f"{psutil.virtual_memory().percent}%",
        'disk': f"{psutil.disk_usage('/').percent}%",
        'cpu': f"{psutil.cpu_percent(interval=1)}%",
    }
    
    # Vérifier Celery
    try:
        from celery_app import app
        inspector = app.control.inspect()
        active = inspector.active() or {}
        health['celery_workers'] = len(active)
    except:
        health['celery_workers'] = 'Error'
    
    # Composer le message
    message = f"""
Rapport de Santé Système - {timezone.now().date()}

Utilisation Ressources:
- CPU: {health['cpu']}
- RAM: {health['memory']}
- Disk: {health['disk']}
- Celery Workers: {health['celery_workers']}

Système: {'✅ Healthy' if all(
    float(v.replace('%', '')) < 80 
    for k, v in health.items() 
    if isinstance(v, str) and '%' in v
) else '⚠️ Attention'}
"""
    
    # Envoyer aux admins
    try:
        send_mail(
            subject='Rapport Hebdomadaire Système',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.ADMINS[0][1]] if settings.ADMINS else [],
        )
        logger.info("Rapport de santé envoyé")
        return "Rapport de santé envoyé aux admins"
    except Exception as e:
        logger.error(f"Erreur envoi rapport: {e}")
        return f"Erreur: {e}"


@shared_task
def optimize_database():
    """
    Optimise la base de données (VACUUM, ANALYZE).
    
    Exécutée une fois par semaine (dimanche 4h).
    """
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            # VACUUM ANALYZE pour PostgreSQL
            cursor.execute("VACUUM ANALYZE")
        
        logger.info("Base de données optimisée")
        return "Database optimized successfully"
    except Exception as e:
        logger.error(f"Erreur optimisation DB: {e}")
        raise
