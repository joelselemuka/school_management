from datetime import timedelta

from django.db import transaction
from attendance.models import AcademicCalendarEvent, SeanceCours, HoraireCours
from common.utils import get_jour_map
from attendance.models import Holiday


class SeanceGenerationService:
    """
    Génère les SeanceCours à partir des HoraireCours existants
    pour une période donnée (date_debut → date_fin).
    """

    @staticmethod
    @transaction.atomic
    def generate_for_horaire(horaire: HoraireCours, date_debut, date_fin) -> int:
        """
        Génère toutes les séances d'un horaire sur une plage de dates.

        Args:
            horaire: instance HoraireCours
            date_debut: date de début (inclusive)
            date_fin: date de fin (inclusive)

        Returns:
            Nombre de séances créées
        """
        jour_map = get_jour_map()

        if horaire.jour not in jour_map:
            return 0

        weekday_target = jour_map[horaire.jour]

        holidays = set(
            Holiday.objects.filter(
                annee_academique=horaire.annee_academique
            ).values_list("date", flat=True)
        )

        # Récupérer les événements calendaires qui suspendent les cours
        suspended_events = list(
            AcademicCalendarEvent.objects.filter(
                annee_academique=horaire.annee_academique,
                suspend_cours=True,
                date_debut__lte=date_fin,
                date_fin__gte=date_debut,
            ).prefetch_related('classes')
        )

        current = date_debut
        seances = []

        while current <= date_fin:
            if current.weekday() == weekday_target:
                is_holiday = current in holidays

                # Vérifier si la date est suspendue pour cette classe
                is_suspended = any(
                    e.applies_to(current, horaire.classe)
                    for e in suspended_events
                )

                seances.append(
                    SeanceCours(
                        horaire=horaire,
                        cours=horaire.cours,
                        classe=horaire.classe,
                        annee_academique=horaire.annee_academique,
                        date=current,
                        is_holiday=is_holiday,
                        is_suspended=is_suspended,
                    )
                )

            current += timedelta(days=1)

        SeanceCours.objects.bulk_create(seances, ignore_conflicts=True)
        return len(seances)

    @staticmethod
    @transaction.atomic
    def generate_for_classe(classe, annee_academique, date_debut=None, date_fin=None) -> dict:
        """
        Génère les séances pour tous les horaires d'une classe.

        Args:
            classe: instance Classe
            annee_academique: instance AnneeAcademique
            date_debut: date de début (défaut: date_debut de l'année académique)
            date_fin: date de fin (défaut: date_fin de l'année académique)

        Returns:
            {'total_seances': int, 'horaires_traites': int}
        """
        if date_debut is None:
            date_debut = annee_academique.date_debut
        if date_fin is None:
            date_fin = annee_academique.date_fin

        horaires = HoraireCours.objects.filter(
            classe=classe,
            annee_academique=annee_academique,
            actif=True
        )

        total = 0
        for horaire in horaires:
            total += SeanceGenerationService.generate_for_horaire(
                horaire, date_debut, date_fin
            )

        return {'total_seances': total, 'horaires_traites': horaires.count()}

    @staticmethod
    def is_suspended(date, classe) -> bool:
        """Vérifie si les cours sont suspendus pour une classe à une date donnée."""
        events = AcademicCalendarEvent.objects.filter(
            annee_academique=classe.annee_academique,
            suspend_cours=True,
            date_debut__lte=date,
            date_fin__gte=date
        )

        for e in events:
            if not e.classes.exists() or classe in e.classes.all():
                return True

        return False