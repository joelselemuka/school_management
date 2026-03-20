"""
Service de génération automatique des horaires de cours.

Algorithme de distribution proportionnelle par volume horaire:
  1. Récupérer la config de la classe (heures_max_par_jour, jours_prolonges)
  2. Calculer le nombre total de créneaux disponibles par semaine
     = somme(heures_par_jour pour chaque jour actif de la semaine)
  3. Calculer le total des volumes horaires de tous les cours
  4. Pour chaque cours, allouer:  floor(volume / total_volume * total_créneaux)
  5. Distribuer les créneaux restants au cours avec le plus grand volume d'abord
  6. Placer les créneaux en évitant les conflits (même classe, même jour, même numero_heure)

Usage:
    HoraireGenerationService.generate_for_classe(classe, annee_academique)
    HoraireGenerationService.generate_for_all_classes(annee_academique)
"""

import math
from collections import defaultdict

from django.db import transaction

from attendance.models import HoraireCours, ClasseHoraireConfig, JOUR_CHOICES
from attendance.services.schedule_config_service import ScheduleConfigService
from common.utils import get_jour_map


JOURS_ORDRE = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI"]


class HoraireGenerationService:

    # ─── Méthode principale : une classe ─────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def generate_for_classe(classe, annee_academique, replace_existing: bool = True) -> dict:
        """
        Génère (ou régénère) les horaires d'une seule classe basé sur le volume horaire.

        Args:
            classe: instance Classe
            annee_academique: instance AnneeAcademique
            replace_existing: si True, soft-delete les horaires existants avant de régénérer

        Returns:
            dict avec 'created', 'skipped', 'errors'
        """
        from academics.models import Cours
        from core.models import Ecole

        ecole = Ecole.objects.filter(actif=True).first()
        if not ecole:
            raise ValueError("Configuration école introuvable.")

        # 1. Récupérer la config horaire de la classe
        try:
            config = ClasseHoraireConfig.objects.get(classe=classe, annee_academique=annee_academique)
            heures_max = config.heures_max_par_jour
            jours_prolonges = set(config.jours_prolonges or [])
        except ClasseHoraireConfig.DoesNotExist:
            heures_max = 6
            jours_prolonges = set()

        # 2. Déterminer les jours ouvrables
        jour_map = get_jour_map()
        jours_actifs = [j for j in JOURS_ORDRE if j in jour_map]

        # 3. Calculer les créneaux disponibles par jour
        # Un jour a `heures_max` créneaux sauf si pas dans jours_prolonges quand heures_max > 6
        def heures_pour_jour(jour: str) -> int:
            if heures_max <= 6:
                return heures_max
            # Si heures_max > 6, seuls les jours_prolonges ont plus de 6h
            return heures_max if jour in jours_prolonges else 6

        # Total créneaux = somme des heures sur tous les jours actifs
        total_creneaux = sum(heures_pour_jour(j) for j in jours_actifs)

        if total_creneaux == 0:
            return {'created': 0, 'skipped': 0, 'errors': ['Aucun créneau disponible.']}

        # 4. Récupérer les cours de la classe avec leur volume
        cours_list = list(
            Cours.objects.filter(
                classe=classe,
                annee_academique=annee_academique,
                actif=True
            ).order_by('-volume_horaire', 'nom')
        )

        if not cours_list:
            return {'created': 0, 'skipped': 0, 'errors': ['Aucun cours actif pour cette classe.']}

        total_volume = sum(c.volume_horaire for c in cours_list)
        if total_volume == 0:
            # Par défaut, distribuons également
            total_volume = len(cours_list)
            for c in cours_list:
                c.volume_horaire = 1

        # 5. Calculer l'allocation par cours (distribution proportionnelle)
        allocations = {}
        for cours in cours_list:
            raw = (cours.volume_horaire / total_volume) * total_creneaux
            allocations[cours.pk] = math.floor(raw)

        # Distribuer les créneaux restants aux cours avec le plus grand remainder
        creneaux_alloues = sum(allocations.values())
        reste = total_creneaux - creneaux_alloues

        # Trier par remainder décroissant pour distribuer le reste
        remainders = {
            c.pk: ((c.volume_horaire / total_volume) * total_creneaux) - math.floor(
                (c.volume_horaire / total_volume) * total_creneaux)
            for c in cours_list
        }
        sorted_by_remainder = sorted(remainders.items(), key=lambda x: -x[1])
        for pk, _ in sorted_by_remainder[:reste]:
            allocations[pk] += 1

        # 6. Générer la grille des créneaux disponibles [('LUNDI', 1), ('LUNDI', 2), ...]
        creneaux_disponibles = []
        for jour in jours_actifs:
            nb = heures_pour_jour(jour)
            for numero in range(1, nb + 1):
                creneaux_disponibles.append((jour, numero))

        # 7. Soft-delete des anciens horaires si replace_existing
        if replace_existing:
            HoraireCours.objects.filter(
                classe=classe,
                annee_academique=annee_academique,
                actif=True
            ).update(actif=False)

        # 8. Créer les nouveaux horaires
        horaires_a_creer = []
        creneaux_index = 0
        errors = []
        created_count = 0

        # On trie les cours par volume décroissant pour les placer en premier
        cours_list_sorted = sorted(cours_list, key=lambda c: -c.volume_horaire)

        for cours in cours_list_sorted:
            nb_heures_allouees = allocations.get(cours.pk, 0)

            for _ in range(nb_heures_allouees):
                if creneaux_index >= len(creneaux_disponibles):
                    errors.append(
                        f"Créneaux insuffisants pour '{cours.nom}' "
                        f"(allocation={nb_heures_allouees})"
                    )
                    break

                jour, numero = creneaux_disponibles[creneaux_index]
                creneaux_index += 1

                # Calculer les heures depuis la config
                slot = ScheduleConfigService.slot_for_numero(numero, ecole)
                if not slot:
                    errors.append(f"Slot H{numero} introuvable dans la config école.")
                    continue

                horaires_a_creer.append(
                    HoraireCours(
                        cours=cours,
                        classe=classe,
                        annee_academique=annee_academique,
                        jour=jour,
                        numero_heure=numero,
                        heure_debut=slot['heure_debut'],
                        heure_fin=slot['heure_fin'],
                    )
                )
                created_count += 1

        # Bulk create
        HoraireCours.objects.bulk_create(horaires_a_creer, ignore_conflicts=True)

        return {
            'created': created_count,
            'skipped': total_creneaux - creneaux_index,
            'errors': errors,
            'total_creneaux': total_creneaux,
            'allocations': {
                cours.nom: allocations.get(cours.pk, 0)
                for cours in cours_list
            }
        }

    # ─── Toutes les classes ───────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def generate_for_all_classes(annee_academique, replace_existing: bool = True) -> dict:
        """
        Génère les horaires pour toutes les classes d'une année académique.

        Returns:
            dict {classe_nom: résultat generate_for_classe()}
        """
        from academics.models import Classe

        classes = Classe.objects.filter(
            annee_academique=annee_academique,
            actif=True
        )

        resultats = {}
        for classe in classes:
            try:
                res = HoraireGenerationService.generate_for_classe(
                    classe, annee_academique, replace_existing=replace_existing
                )
                resultats[classe.nom] = res
            except Exception as e:
                resultats[classe.nom] = {'created': 0, 'errors': [str(e)]}

        return resultats

    # ─── Détection de conflits ────────────────────────────────────────────────

    @staticmethod
    def detect_conflicts(classe=None, annee_academique=None) -> list:
        """
        Détecte les conflits d'horaires (même classe, même jour, même numero_heure).

        Args:
            classe: filtrer par classe (optionnel)
            annee_academique: filtrer par année (optionnel)

        Returns:
            liste de dicts décrivant chaque conflit
        """
        from django.db.models import Count
        from attendance.models import HoraireCours

        qs = HoraireCours.objects.filter(actif=True)
        if classe:
            qs = qs.filter(classe=classe)
        if annee_academique:
            qs = qs.filter(annee_academique=annee_academique)

        # Grouper par (classe, jour, numero_heure) et trouver les doublons
        from django.db.models import Count
        conflits_qs = (
            qs.values('classe', 'annee_academique', 'jour', 'numero_heure')
            .annotate(nb=Count('id'))
            .filter(nb__gt=1)
        )

        conflits = []
        for item in conflits_qs:
            horaires = HoraireCours.objects.filter(
                classe_id=item['classe'],
                annee_academique_id=item['annee_academique'],
                jour=item['jour'],
                numero_heure=item['numero_heure'],
                actif=True
            ).select_related('cours', 'classe')

            conflits.append({
                'classe': horaires.first().classe.nom if horaires.exists() else '?',
                'jour': item['jour'],
                'numero_heure': item['numero_heure'],
                'cours_en_conflit': [h.cours.nom for h in horaires],
            })

        return conflits
