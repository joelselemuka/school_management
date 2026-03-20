"""
Service de calcul des plages horaires basé sur la configuration de l'école.

À partir de:
  - heure_debut_cours (ex: 07:30)
  - duree_heure_etude (ex: 50 min)
  - heure_recreation_apres (ex: 3 → récré après la 3e heure)
  - duree_recreation (ex: 30 min)

Ce service calcule automatiquement les plages de chaque heure d'étude.

Exemple de résultat avec heure_debut=07:30, dur=50, récré_après=3, dur_récré=30:
  H1: 07:30 → 08:20
  H2: 08:20 → 09:10
  H3: 09:10 → 10:00
  [Récré: 10:00 → 10:30]
  H4: 10:30 → 11:20
  H5: 11:20 → 12:10
  ...
"""

from datetime import datetime, timedelta, time as time_type


class ScheduleConfigService:

    @staticmethod
    def get_ecole():
        """Retourne la configuration active de l'école."""
        from core.models import Ecole
        ecole = Ecole.objects.filter(actif=True).first()
        if not ecole:
            raise ValueError("Configuration école introuvable.")
        return ecole

    @staticmethod
    def _time_to_minutes(t: time_type) -> int:
        """Convertit un objet time en nombre de minutes depuis minuit."""
        return t.hour * 60 + t.minute

    @staticmethod
    def _minutes_to_time(minutes: int) -> time_type:
        """Convertit des minutes depuis minuit en objet time."""
        h, m = divmod(minutes, 60)
        if h >= 24:
            raise ValueError(f"L'heure calculée dépasse minuit ({minutes} min).")
        return time_type(h, m)

    @classmethod
    def get_time_slots(cls, ecole=None, nb_heures: int = 8) -> list:
        """
        Calcule et retourne la liste des plages horaires pour nb_heures heures d'étude.

        Retourne une liste de dicts:
          [
            {'numero': 1, 'heure_debut': time(7, 30), 'heure_fin': time(8, 20), 'is_recreation_before': False},
            {'numero': 2, ...},
            ...
            {'numero': None, 'label': 'Récréation', 'heure_debut': ..., 'heure_fin': ..., 'is_recreation': True},
            ...
          ]
        """
        if ecole is None:
            ecole = cls.get_ecole()

        current_minutes = cls._time_to_minutes(ecole.heure_debut_cours)
        duree = ecole.duree_heure_etude
        recre_apres = ecole.heure_recreation_apres
        duree_recre = ecole.duree_recreation

        slots = []
        for numero in range(1, nb_heures + 1):
            heure_debut_slot = cls._minutes_to_time(current_minutes)
            current_minutes += duree
            heure_fin_slot = cls._minutes_to_time(current_minutes)

            slots.append({
                'numero': numero,
                'heure_debut': heure_debut_slot,
                'heure_fin': heure_fin_slot,
                'is_recreation': False,
                'label': f"{numero}{'ère' if numero == 1 else 'e'} heure",
            })

            # Insérer la récréation après l'heure spécifiée
            if numero == recre_apres:
                recre_debut = cls._minutes_to_time(current_minutes)
                current_minutes += duree_recre
                recre_fin = cls._minutes_to_time(current_minutes)
                slots.append({
                    'numero': None,
                    'heure_debut': recre_debut,
                    'heure_fin': recre_fin,
                    'is_recreation': True,
                    'label': 'Récréation',
                })

        return slots

    @classmethod
    def get_study_slots_only(cls, ecole=None, nb_heures: int = 8) -> list:
        """Retourne uniquement les plages d'étude (sans récréation)."""
        return [
            s for s in cls.get_time_slots(ecole, nb_heures)
            if not s['is_recreation']
        ]

    @classmethod
    def slot_for_numero(cls, numero: int, ecole=None) -> dict | None:
        """Retourne la plage horaire pour un numéro d'heure donné."""
        ecole = ecole or cls.get_ecole()
        # On génère jusqu'au numéro demandé (max 12)
        slots = cls.get_study_slots_only(ecole, nb_heures=max(numero, 12))
        for slot in slots:
            if slot['numero'] == numero:
                return slot
        return None

    @classmethod
    def get_slots_as_schedule_display(cls, ecole=None, nb_heures: int = 8) -> list:
        """
        Retourne les plages sous forme lisible pour affichage dans l'API.

        Ex: [{'numero': 1, 'plage': '07h30 – 08h20'}, ...]
        """
        result = []
        for slot in cls.get_time_slots(ecole, nb_heures):
            debut = slot['heure_debut'].strftime('%Hh%M')
            fin = slot['heure_fin'].strftime('%Hh%M')
            result.append({
                'numero': slot['numero'],
                'label': slot['label'],
                'plage': f"{debut} – {fin}",
                'heure_debut': slot['heure_debut'].strftime('%H:%M'),
                'heure_fin': slot['heure_fin'].strftime('%H:%M'),
                'is_recreation': slot['is_recreation'],
            })
        return result
