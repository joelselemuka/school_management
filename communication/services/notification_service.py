from communication.models import Notification,  NotificationUser
from communication.services.email_service import EmailService
from communication.services.websocket_service import WebSocketService
from users.models import ParentEleve

class RecipientResolver:

    @staticmethod
    def resolve(event,context):

        if event == "INSCRIPTION_VALIDEE":
            return ParentEleve.get_users(context["eleve"])

        if event == "PAIEMENT_EFFECTUE":
            return ParentEleve.get_users(context["eleve"])


from django.db import transaction
from django.utils import timezone


class NotificationService:

    # ======================================
    # CORE CREATE
    # ======================================
    @staticmethod
    @transaction.atomic
    def create_notification_for_users(
        *,
        users,
        titre,
        message,
        notif_type="info",
        metadata=None,
    ):
        """
        Crée une notification + recipients en bulk.
        Production ready.
        """

        if not users:
            return None

        # 🧾 notification principale
        notification = Notification.objects.create(
            titre=titre,
            message=message,
            type=notif_type,
            metadata=metadata or {},
        )

        # 👥 recipients bulk
        notif_users = [
            NotificationUser(
                notification=notification,
                user=user,
            )
            for user in users
            if user is not None
        ]

        NotificationUser.objects.bulk_create(
            notif_users,
            batch_size=500,
            ignore_conflicts=True,  # 🔥 anti-doublon
        )

        return notification

   # FRAIS CREATED
    # ======================================
    @staticmethod
    @transaction.atomic
    def notify_frais_created(frais):
        """
        Notifie élèves + parents concernés.
        Ultra scalable.
        """

        students = frais.get_target_students()

        if not students.exists():
            return None

        users_to_notify = []

        for student in students.select_related("parent", "user"):

            # élève
            if getattr(student, "user", None):
                users_to_notify.append(student.user)

            # parent
            parent_user = getattr(student.parent, "user", None)
            if parent_user:
                users_to_notify.append(parent_user)

        if not users_to_notify:
            return None

        titre = "Nouveau frais scolaire"
        message = (
            f"Un nouveau frais '{frais.name}' de {frais.amount} a été ajouté."
        )

        metadata = {
            "frais_id": frais.id,
        }

        return NotificationService.create_notification_for_users(
            users=users_to_notify,
            titre=titre,
            message=message,
            notif_type="finance",
            metadata=metadata,
        ) 
    
    
    @staticmethod
    @transaction.atomic
    def notify_payment_done(payment):

        student = payment.student
        parent = getattr(student, "parent", None)

        users = []

        if getattr(student, "user", None):
            users.append(student.user)

        parent_user = getattr(parent, "user", None)
        if parent_user:
            users.append(parent_user)

        if not users:
            return None

        titre = "Paiement reçu"

        message = (
            f"Paiement de {payment.amount} reçu. "
            f"Reste à payer: {payment.remaining_amount}"
        )

        metadata = {
            "payment_id": payment.id,
            "frais_id": payment.frais_id,
        }

        return NotificationService.create_notification_for_users(
            users=users,
            titre=titre,
            message=message,
            notif_type="finance",
            metadata=metadata,
        )
    
    @staticmethod
    def mark_as_read(notification_user):
        notification_user.is_read = True
        notification_user.read_at = timezone.now()
        notification_user.save(update_fields=["is_read", "read_at"])
    
    @staticmethod
    def notify_absence(presence):

        eleve = presence.eleve
        parents = eleve.parents.all()

        for parent in parents:
            Notification.objects.create(
                titre="Absence enregistrée",
                message=f"{eleve} est {presence.get_statut_display()} le {presence.seance.date}",
                type="alerte"
            ).targets.add(parent.user)

    