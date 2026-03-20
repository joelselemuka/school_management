from attendance.models import Presence


class AttendanceStatsService:

    @staticmethod
    def for_classe(classe, periode):

        qs = Presence.objects.filter(
            seance__classe=classe,
            seance__date__range=(periode.date_debut, periode.date_fin)
        )

        return {
            "present": qs.filter(statut="present").count(),
            "absent": qs.filter(statut="absent").count(),
            "retard": qs.filter(statut="retard").count(),
        }
