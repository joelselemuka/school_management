from django.db import transaction

from attendance.models import Presence
from attendance.services.disciplineService import DisciplineService

class PresenceService:

    @staticmethod
    @transaction.atomic
    def mark_presence(seance, eleve, statut, user):

        if seance.is_holiday:
            raise ValueError("Séance fériée : aucune présence possible")

        if seance.is_locked:
            raise ValueError("Séance verrouillée")

        presence, _ = Presence.objects.update_or_create(
            eleve=eleve,
            seance=seance,
            defaults={"statut": statut}
        )

        DisciplineService.evaluate(eleve)

        return presence
