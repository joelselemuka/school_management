from django.db.models import Count

from core.models import Periode
from attendance.models import Presence


class AttendanceStatisticsService:

    @staticmethod
    def stats_eleve(eleve, periode: Periode):
        qs = Presence.objects.filter(
            eleve=eleve,
            seance__date__range=(periode.date_debut, periode.date_fin),
            actif=True
        )

        total = qs.count() or 1

        data = qs.values("statut").annotate(total=Count("id"))

        stats = {row["statut"]: row["total"] for row in data}

        return {
            "total_seances": total,
            "present": stats.get("present", 0),
            "absent": stats.get("absent", 0),
            "retard": stats.get("retard", 0),
            "malade": stats.get("malade", 0),
            "taux_absence": round((stats.get("absent", 0) / total) * 100, 2)
        }

    @staticmethod
    def stats_classe(classe, periode: Periode):
        qs = Presence.objects.filter(
            seance__classe=classe,
            seance__date__range=(periode.date_debut, periode.date_fin),
            actif=True
        )

        total = qs.count() or 1

        stats = qs.values("statut").annotate(total=Count("id"))

        return {
            "total_enregistrements": total,
            "repartition": {s["statut"]: s["total"] for s in stats}
        }
