"""
Service de gestion des horaires enseignants.

L'horaire d'un enseignant est dérivé automatiquement depuis:
  - HoraireCours (cours planifiés dans une classe)
  - AffectationEnseignant (qui enseigne quel cours)

Usage:
    TeacherScheduleService.generate_teacher_schedules(annee_academique)
    TeacherScheduleService.get_schedule_for_teacher(enseignant, annee_academique)
"""

from django.db import transaction


class TeacherScheduleService:

    # ─── Génération des horaires enseignants ──────────────────────────────────

    @staticmethod
    @transaction.atomic
    def generate_teacher_schedules(annee_academique, replace_existing: bool = True) -> dict:
        """
        Génère les HoraireEnseignant pour tous les profs basé sur
        HoraireCours + AffectationEnseignant.

        Returns:
            dict {'created': int, 'skipped': int, 'conflicts': list}
        """
        from attendance.models import HoraireEnseignant, HoraireCours
        from academics.models import AffectationEnseignant

        if replace_existing:
            HoraireEnseignant.objects.filter(
                annee_academique=annee_academique
            ).delete()

        # Récupérer tous les horaires actifs de l'année
        horaires = HoraireCours.objects.filter(
            annee_academique=annee_academique,
            actif=True
        ).select_related('cours', 'classe')

        # Récupérer les affectations pour les cours de cette année
        affectations = AffectationEnseignant.objects.filter(
            cours__annee_academique=annee_academique,
            actif=True
        ).select_related('teacher', 'cours')

        # Construire un dict cours_id -> liste d'enseignants
        cours_to_teachers = {}
        for aff in affectations:
            cours_to_teachers.setdefault(aff.cours_id, []).append(aff.teacher)

        to_create = []
        skipped = 0
        conflicts = []

        # Pour chaque horaire, créer l'entrée HoraireEnseignant pour chaque prof affecté
        for horaire in horaires:
            teachers = cours_to_teachers.get(horaire.cours_id, [])
            if not teachers:
                skipped += 1
                continue

            for teacher in teachers:
                # Vérifier conflit: même enseignant, même jour, même heure
                conflict = TeacherScheduleService._check_teacher_conflict(
                    teacher, horaire, to_create
                )
                if conflict:
                    conflicts.append({
                        'enseignant': str(teacher),
                        'jour': horaire.jour,
                        'numero_heure': horaire.numero_heure,
                        'cours_1': conflict,
                        'cours_2': horaire.cours.nom,
                    })
                    skipped += 1
                    continue

                to_create.append(
                    HoraireEnseignant(
                        enseignant=teacher,
                        horaire_cours=horaire,
                        annee_academique=annee_academique,
                    )
                )

        HoraireEnseignant.objects.bulk_create(to_create, ignore_conflicts=True)

        return {
            'created': len(to_create),
            'skipped': skipped,
            'conflicts': conflicts,
        }

    @staticmethod
    def _check_teacher_conflict(teacher, horaire, pending_list: list) -> str | None:
        """
        Vérifie si un enseignant a déjà un cours planifié au même moment
        dans la liste des HoraireEnseignant en cours de création.

        Returns:
            le nom du cours en conflit, ou None si pas de conflit.
        """
        for he in pending_list:
            if (
                he.enseignant_id == teacher.pk
                and he.horaire_cours.jour == horaire.jour
                and he.horaire_cours.numero_heure == horaire.numero_heure
                and he.horaire_cours.numero_heure is not None
            ):
                return he.horaire_cours.cours.nom
        return None

    # ─── Lecture de l'horaire d'un enseignant ─────────────────────────────────

    @staticmethod
    def get_schedule_for_teacher(enseignant, annee_academique) -> dict:
        """
        Retourne l'horaire d'un enseignant groupé par jour.

        Returns:
            dict {
                'LUNDI': [
                    {'numero_heure': 1, 'heure_debut': '07:30', 'heure_fin': '08:20',
                     'cours': 'Mathématiques', 'classe': '6e A', 'salle': 'A101'},
                    ...
                ],
                ...
            }
        """
        from attendance.models import HoraireEnseignant

        horaires = (
            HoraireEnseignant.objects
            .filter(
                enseignant=enseignant,
                annee_academique=annee_academique
            )
            .select_related('horaire_cours__cours', 'horaire_cours__classe')
            .order_by('horaire_cours__jour', 'horaire_cours__numero_heure')
        )

        JOURS_ORDRE = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI"]
        schedule = {jour: [] for jour in JOURS_ORDRE}

        for he in horaires:
            hc = he.horaire_cours
            entry = {
                'horaire_id': hc.pk,
                'numero_heure': hc.numero_heure,
                'heure_debut': hc.heure_debut.strftime('%H:%M') if hc.heure_debut else None,
                'heure_fin': hc.heure_fin.strftime('%H:%M') if hc.heure_fin else None,
                'cours': hc.cours.nom,
                'cours_id': hc.cours_id,
                'classe': hc.classe.nom,
                'classe_id': hc.classe_id,
                'salle': hc.salle or '',
            }
            if hc.jour in schedule:
                schedule[hc.jour].append(entry)

        # Supprimer les jours vides
        return {jour: slots for jour, slots in schedule.items() if slots}

    @staticmethod
    def detect_conflicts_teacher(enseignant, annee_academique) -> list:
        """
        Détecte si un enseignant a deux cours planifiés au même moment.

        Returns:
            liste de conflits [{'jour', 'numero_heure', 'cours_en_conflit': [...]}]
        """
        from attendance.models import HoraireEnseignant
        from django.db.models import Count

        # Trouver les doublons (même enseignant, même jour, même numero_heure)
        conflits_qs = (
            HoraireEnseignant.objects
            .filter(enseignant=enseignant, annee_academique=annee_academique)
            .values('horaire_cours__jour', 'horaire_cours__numero_heure')
            .annotate(nb=Count('id'))
            .filter(nb__gt=1)
        )

        conflits = []
        for item in conflits_qs:
            horaires = (
                HoraireEnseignant.objects
                .filter(
                    enseignant=enseignant,
                    annee_academique=annee_academique,
                    horaire_cours__jour=item['horaire_cours__jour'],
                    horaire_cours__numero_heure=item['horaire_cours__numero_heure'],
                )
                .select_related('horaire_cours__cours', 'horaire_cours__classe')
            )
            conflits.append({
                'jour': item['horaire_cours__jour'],
                'numero_heure': item['horaire_cours__numero_heure'],
                'cours_en_conflit': [
                    f"{he.horaire_cours.cours.nom} ({he.horaire_cours.classe.nom})"
                    for he in horaires
                ],
            })

        return conflits

    @staticmethod
    def get_weekly_hours_for_teacher(enseignant, annee_academique) -> dict:
        """
        Retourne un résumé des heures d'enseignement par cours/classe.

        Returns:
            {'total_heures': int, 'par_cours': [{'cours', 'classe', 'heures_semaine'}]}
        """
        from attendance.models import HoraireEnseignant
        from django.db.models import Count

        stats = (
            HoraireEnseignant.objects
            .filter(enseignant=enseignant, annee_academique=annee_academique)
            .values('horaire_cours__cours__nom', 'horaire_cours__classe__nom')
            .annotate(heures=Count('id'))
            .order_by('-heures')
        )

        par_cours = [
            {
                'cours': s['horaire_cours__cours__nom'],
                'classe': s['horaire_cours__classe__nom'],
                'heures_semaine': s['heures'],
            }
            for s in stats
        ]
        total = sum(s['heures_semaine'] for s in par_cours)

        return {
            'enseignant': str(enseignant),
            'total_heures_semaine': total,
            'par_cours': par_cours,
        }
