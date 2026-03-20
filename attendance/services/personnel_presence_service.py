"""
Service de gestion de la présence du personnel.

Responsabilités :
  - Enregistrement / mise à jour d'une présence journalière
  - Calcul du sommaire mensuel (nb_jours_absence, nb_jours_congé, etc.)
  - Intégration avec la paie : fournit nb_jours_absence pour BulletinSalaire
"""

import logging
from calendar import monthrange
from datetime import date

from django.db import transaction
from django.db.models import Count, Q
from django.core.exceptions import ValidationError

from attendance.models import PresencePersonnel, SommairePaiePersonnel

logger = logging.getLogger(__name__)


class PersonnelPresenceService:
    """Service centralisé pour la gestion des présences du personnel."""

    # ── Enregistrement ────────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def enregistrer_presence(personnel, date_jour: date, statut: str,
                             enregistre_par=None, remplacant=None,
                             conge_justifie: bool = False, remarque: str = ""):
        """
        Crée ou met à jour la présence d'un personnel pour une journée.

        Args:
            personnel        : instance de Personnel
            date_jour        : date du jour concerné
            statut           : 'present' | 'absent' | 'retard' | 'remplace' | 'conge'
            enregistre_par   : User ayant saisi la présence
            remplacant       : Personnel remplaçant (si statut='remplace')
            conge_justifie   : True si absence payée (non déduite de la paie)
            remarque         : note libre

        Returns:
            (PresencePersonnel, created: bool)
        """
        STATUTS_VALIDES = {"present", "absent", "retard", "remplace", "conge"}
        if statut not in STATUTS_VALIDES:
            raise ValidationError(
                f"Statut invalide : '{statut}'. Valeurs autorisées : {STATUTS_VALIDES}"
            )

        if statut == "remplace" and remplacant is None:
            raise ValidationError(
                "Un remplaçant doit être fourni lorsque le statut est 'remplace'."
            )

        presence, created = PresencePersonnel.objects.update_or_create(
            personnel=personnel,
            date=date_jour,
            defaults={
                "statut": statut,
                "remplacant": remplacant,
                "conge_justifie": conge_justifie if statut in ("absent", "conge") else False,
                "remarque": remarque,
                "enregistre_par": enregistre_par,
            },
        )

        logger.info(
            "[Présence personnel] %s %s — %s (%s)",
            "Créée" if created else "Mise à jour",
            personnel, date_jour, statut,
        )

        # Mettre à jour le sommaire mensuel automatiquement
        PersonnelPresenceService.recalculer_sommaire(
            personnel, date_jour.month, date_jour.year
        )

        return presence, created

    @staticmethod
    @transaction.atomic
    def enregistrer_presences_masse(date_jour: date, presences_data: list,
                                    enregistre_par=None):
        """
        Enregistre les présences de plusieurs personnels en une seule transaction.

        Args:
            date_jour       : date commune à toutes les présences
            presences_data  : liste de dicts { personnel, statut, conge_justifie?,
                              remplacant?, remarque? }
            enregistre_par  : User qui saisit

        Returns:
            dict { created: int, updated: int, errors: list }
        """
        results = {"created": 0, "updated": 0, "errors": []}
        personnels_a_recalculer = set()

        for data in presences_data:
            try:
                _, created = PersonnelPresenceService.enregistrer_presence(
                    personnel=data["personnel"],
                    date_jour=date_jour,
                    statut=data["statut"],
                    enregistre_par=enregistre_par,
                    remplacant=data.get("remplacant"),
                    conge_justifie=data.get("conge_justifie", False),
                    remarque=data.get("remarque", ""),
                )
                if created:
                    results["created"] += 1
                else:
                    results["updated"] += 1
                personnels_a_recalculer.add(data["personnel"])
            except Exception as exc:
                results["errors"].append({
                    "personnel": str(data.get("personnel", "?")),
                    "erreur": str(exc),
                })

        return results

    # ── Sommaire mensuel ──────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def recalculer_sommaire(personnel, mois: int, annee: int):
        """
        Recalcule et persiste le SommairePaiePersonnel pour un mois/année.

        Ce sommaire est utilisé directement par BulletinSalaireService
        pour pré-remplir le champ nb_jours_absence du bulletin.

        Returns:
            SommairePaiePersonnel
        """
        presences_qs = PresencePersonnel.objects.filter(
            personnel=personnel,
            date__month=mois,
            date__year=annee,
            actif=True,
        )

        stats = presences_qs.aggregate(
            travailles=Count("id", filter=Q(statut="present")),
            absents=Count("id", filter=Q(statut="absent", conge_justifie=False)),
            conges=Count("id", filter=Q(statut__in=["absent", "conge"], conge_justifie=True)),
            retards=Count("id", filter=Q(statut="retard")),
        )

        sommaire, _ = SommairePaiePersonnel.objects.update_or_create(
            personnel=personnel,
            mois=mois,
            annee=annee,
            defaults={
                "nb_jours_travailles": stats["travailles"] or 0,
                "nb_jours_absence": stats["absents"] or 0,
                "nb_jours_conge": stats["conges"] or 0,
                "nb_jours_retard": stats["retards"] or 0,
            },
        )

        logger.debug(
            "[Sommaire paie] %s %02d/%d → absence=%d congé=%d",
            personnel, mois, annee, sommaire.nb_jours_absence, sommaire.nb_jours_conge,
        )
        return sommaire

    # ── Requêtes ──────────────────────────────────────────────────────────────

    @staticmethod
    def get_absences_mois(personnel, mois: int, annee: int) -> int:
        """
        Retourne le nombre de jours d'absence non justifiée pour un mois.
        Essaie d'abord le sommaire pré-calculé, sinon recalcule à la volée.
        """
        try:
            sommaire = SommairePaiePersonnel.objects.get(
                personnel=personnel, mois=mois, annee=annee
            )
            return sommaire.nb_jours_absence
        except SommairePaiePersonnel.DoesNotExist:
            # Recalcul à la volée si sommaire absent
            sommaire = PersonnelPresenceService.recalculer_sommaire(
                personnel, mois, annee
            )
            return sommaire.nb_jours_absence

    @staticmethod
    def get_statistiques_mois(personnel, mois: int, annee: int) -> dict:
        """
        Retourne un dict complet des statistiques de présence pour le mois.
        Utilisé par les vues et les rapports.
        """
        try:
            sommaire = SommairePaiePersonnel.objects.get(
                personnel=personnel, mois=mois, annee=annee
            )
        except SommairePaiePersonnel.DoesNotExist:
            sommaire = PersonnelPresenceService.recalculer_sommaire(
                personnel, mois, annee
            )

        _, nb_jours_du_mois = monthrange(annee, mois)
        presences = list(
            PresencePersonnel.objects.filter(
                personnel=personnel,
                date__month=mois,
                date__year=annee,
                actif=True,
            ).order_by("date").values("date", "statut", "conge_justifie", "remarque")
        )

        return {
            "personnel_id": personnel.pk,
            "personnel_nom": str(personnel),
            "mois": mois,
            "annee": annee,
            "nb_jours_du_mois": nb_jours_du_mois,
            "nb_jours_travailles": sommaire.nb_jours_travailles,
            "nb_jours_absence_non_justifiee": sommaire.nb_jours_absence,
            "nb_jours_conge": sommaire.nb_jours_conge,
            "nb_jours_retard": sommaire.nb_jours_retard,
            "detail_presences": presences,
        }

    @staticmethod
    def get_sommaire_ou_none(personnel, mois: int, annee: int):
        """Retourne le SommairePaiePersonnel ou None s'il n'existe pas."""
        try:
            return SommairePaiePersonnel.objects.get(
                personnel=personnel, mois=mois, annee=annee
            )
        except SommairePaiePersonnel.DoesNotExist:
            return None
