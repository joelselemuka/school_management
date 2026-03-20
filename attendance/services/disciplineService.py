from django.db import transaction

from attendance.models import DisciplineRecord, DisciplineRule, Presence

# class DisciplineService:

#     @staticmethod
#     def evaluate(eleve):

#         absences = Presence.objects.filter(
#             eleve=eleve,
#             statut__in=["absent","retard"],
#             actif=True
#         ).count()

#         rule = DisciplineRule.objects.filter(
#             seuil__lte=absences,
#             actif=True
#         ).order_by("-seuil").first()

#         if rule:
#             DisciplineRecord.objects.create(
#                 eleve=eleve,
#                 niveau=rule.niveau
#             )

from attendance.models import DisciplineRule, DisciplineRecord, Presence

class DisciplineService:

    @staticmethod
    def evaluate_eleve(eleve, periode):
        absences = Presence.objects.filter(
            eleve=eleve,
            statut="absent",
            seance__date__range=(periode.date_debut, periode.date_fin),
            actif=True
        ).count()

        rules = DisciplineRule.objects.filter(actif=True).order_by("seuil")

        for rule in rules:
            if absences >= rule.seuil:
                DisciplineRecord.objects.get_or_create(
                    eleve=eleve,
                    niveau=rule.niveau
                )
