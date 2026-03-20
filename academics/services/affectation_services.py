from django.db import transaction
from django.core.exceptions import ValidationError
from academics.models import AffectationEnseignant


class AffectationService:


    @staticmethod
    def list():

        return AffectationEnseignant.objects.select_related(
            "teacher__user",
            "cours__classe"
        )


    @staticmethod
    def get(pk):

        return AffectationEnseignant.objects.select_related(
            "teacher__user",
            "cours"
        ).get(pk=pk)


    @staticmethod
    @transaction.atomic
    def create(data):
        """
        Crée une affectation enseignant-cours.
        Vérifie que l'enseignant a un contrat actif non expiré.
        """
        teacher = data.get("teacher")

        if teacher and teacher.fonction == "enseignant":
            from paie.models import ContratEmploye

            contrat_actif = ContratEmploye.objects.filter(
                personnel=teacher, statut="ACTIF"
            ).first()

            if not contrat_actif:
                raise ValidationError(
                    f"L'enseignant {teacher} n'a aucun contrat actif. "
                    f"Impossible de l'affecter à un cours."
                )

            if contrat_actif.is_expired:
                raise ValidationError(
                    f"Le contrat de l'enseignant {teacher} est expiré "
                    f"(date de fin : {contrat_actif.date_fin}). "
                    f"Veuillez renouveler le contrat avant d'affecter cet enseignant."
                )

        affectation = AffectationEnseignant.objects.create(**data)

        # Ajouter un avertissement si le contrat expire bientôt
        if teacher and teacher.fonction == "enseignant":
            from paie.models import ContratEmploye
            contrat = ContratEmploye.objects.filter(
                personnel=teacher, statut="ACTIF"
            ).first()
            if contrat and contrat.is_expiring_soon:
                affectation._contrat_warning = (
                    f"Attention : le contrat de {teacher} expire dans "
                    f"{contrat.days_until_expiry} jours (le {contrat.date_fin})."
                )

        return affectation


    @staticmethod
    @transaction.atomic
    def update(pk, data):

        obj = AffectationEnseignant.objects.get(pk=pk)

        for attr, value in data.items():

            setattr(obj, attr, value)

        obj.save()

        return obj


    @staticmethod
    @transaction.atomic
    def delete(pk):

        AffectationEnseignant.objects.get(pk=pk).soft_delete()