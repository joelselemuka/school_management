"""
Tâches Celery pour les communications (emails, notifications).
"""

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

User = get_user_model()


@shared_task(bind=True, max_retries=3)
def send_email_notification(self, user_id, subject, message):
    """
    Envoie un email à un utilisateur.
    
    Args:
        user_id: ID de l'utilisateur
        subject: Sujet de l'email
        message: Contenu de l'email
    """
    try:
        user = User.objects.get(id=user_id)
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        return f"Email envoyé à {user.email}"
    except Exception as e:
        # Réessayer en cas d'échec
        raise self.retry(exc=e, countdown=60)


@shared_task
def send_bulk_notifications(user_ids, title, message, notification_type='info'):
    """
    Envoie des notifications à plusieurs utilisateurs.
    
    Args:
        user_ids: Liste des IDs utilisateurs
        title: Titre de la notification
        message: Message de la notification
        notification_type: Type de notification
    """
    from communication.models import Notification
    
    channel_layer = get_channel_layer()
    count = 0
    
    for user_id in user_ids:
        try:
            # Créer la notification en base
            notif = Notification.objects.create(
                recipient_id=user_id,
                title=title,
                message=message,
                notification_type=notification_type,
            )
            
            # Envoyer via WebSocket si l'utilisateur est connecté
            async_to_sync(channel_layer.group_send)(
                f'notifications_{user_id}',
                {
                    'type': 'notification_message',
                    'notification_id': notif.id,
                    'title': title,
                    'message': message,
                    'notification_type': notification_type,
                    'timestamp': notif.created_at.isoformat(),
                }
            )
            count += 1
        except Exception as e:
            print(f"Erreur envoi notification à {user_id}: {e}")
    
    return f"{count} notifications envoyées"


@shared_task
def send_daily_notifications():
    """
    Tâche planifiée: Envoie quotidien des notifications groupées.
    
    Exécutée chaque jour à 8h via Celery Beat.
    """
    from communication.models import Notification
    from datetime import datetime, timedelta
    
    yesterday = datetime.now() - timedelta(days=1)
    
    # Récupérer les utilisateurs avec des notifications non lues
    users_with_unread = User.objects.filter(
        received_notifications__read=False,
        received_notifications__created_at__gte=yesterday
    ).distinct()
    
    for user in users_with_unread:
        unread_count = user.received_notifications.filter(read=False).count()
        
        # Envoyer un email récapitulatif
        send_email_notification.delay(
            user.id,
            f"Vous avez {unread_count} notification(s) non lue(s)",
            f"Bonjour {user.get_full_name()},\n\n"
            f"Vous avez {unread_count} notification(s) en attente.\n"
            f"Connectez-vous pour les consulter.\n\n"
            f"Cordialement,\nL'équipe"
        )
    
    return f"Emails envoyés à {users_with_unread.count()} utilisateurs"


@shared_task
def send_sms_notification(phone_number, message):
    """
    Envoie un SMS (à intégrer avec un fournisseur SMS).
    
    Args:
        phone_number: Numéro de téléphone
        message: Contenu du SMS
    """
    # TODO: Intégrer avec un provider SMS (Twilio, AfricasTalking, etc.)
    print(f"SMS à {phone_number}: {message}")
    return f"SMS envoyé à {phone_number}"


@shared_task
def cleanup_old_notifications():
    """
    Nettoie les anciennes notifications (> 6 mois).
    """
    from communication.models import Notification
    from datetime import datetime, timedelta
    
    six_months_ago = datetime.now() - timedelta(days=180)
    
    deleted_count, _ = Notification.objects.filter(
        created_at__lt=six_months_ago,
        read=True
    ).delete()
    return f"{deleted_count} notifications supprimées"

@shared_task(bind=True, max_retries=3)
def send_webhook_event(self, event_name, payload):
    """
    Envoie un événement Webhook à tous les endpoints abonnés.
    """
    from communication.models import WebhookEndpoint, WebhookDelivery
    import requests
    import json
    import hmac
    import hashlib
    
    endpoints = WebhookEndpoint.objects.filter(is_active=True).filter(events__contains=event_name)
    count = 0
    
    for endpoint in endpoints:
        headers = {'Content-Type': 'application/json'}
        data_str = json.dumps(payload)
        
        if endpoint.secret:
            signature = hmac.new(
                endpoint.secret.encode('utf-8'),
                data_str.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            headers['X-Signature'] = f"sha256={signature}"
            
        try:
            response = requests.post(endpoint.url, data=data_str, headers=headers, timeout=10)
            success = 200 <= response.status_code < 300
            
            WebhookDelivery.objects.create(
                endpoint=endpoint,
                event_name=event_name,
                payload=payload,
                status_code=response.status_code,
                response_body=response.text[:1000],
                success=success
            )
            count += 1
        except Exception as e:
            WebhookDelivery.objects.create(
                endpoint=endpoint,
                event_name=event_name,
                payload=payload,
                response_body=str(e),
                success=False
            )
            
    return f"Webhook '{event_name}' sent to {count} endpoints"
