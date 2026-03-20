from communication.services.notification_service import NotificationService


class JustificationService:

    @staticmethod
    def validate(justification, admin):

        justification.valide = True
        justification.save()

        presence = justification.presence
        presence.statut = "justifie"
        presence.save()

        NotificationService.trigger(
            "ABSENCE_JUSTIFIEE",
            {"eleve": presence.eleve}
        )
