from attendance.models import AttendanceSummary, Presence





class AttendanceSummaryService:
    MAX_ABSENCES = 5

    @staticmethod
    def recompute(eleve, periode):
        absences = Presence.objects.filter(
            eleve=eleve,
            seance__date__range=(periode.date_debut, periode.date_fin),
            statut="absent"
        ).count()

        summary, _ = AttendanceSummary.objects.update_or_create(
            eleve=eleve,
            periode=periode,
            defaults={
                "absences": absences,
                "is_blocking": absences >= AttendanceSummaryService.MAX_ABSENCES
            }
        )
        return summary





