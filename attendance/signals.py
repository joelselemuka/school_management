"""
Signals pour le module attendance.

- Alerte parents en temps réel quand un élève est marqué absent.
- Recalcul automatique du sommaire paie quand une présence personnel change.
"""

import logging
from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)


@receiver(post_save, sender="attendance.Presence")
def alerter_parents_sur_absence(sender, instance, created, **kwargs):
    """
    Notifie les parents d'un élève dès qu'une absence est enregistrée.
    Utilise le système de Notification existant (communication app).
    """
    if instance.statut != "absent":
        return

    try:
        from communication.models import Notification, NotificationUser
        from users.models import ParentEleve

        eleve = instance.eleve
        seance = instance.seance

        titre = f"Absence signalée — {eleve.nom} {eleve.prenom}"
        message = (
            f"{eleve.nom} {eleve.postnom} {eleve.prenom} a été marqué(e) absent(e) "
            f"lors du cours de {seance.cours.nom} le {seance.date.strftime('%d/%m/%Y')}."
        )

        notif = Notification.objects.create(
            titre=titre,
            message=message,
            type="alerte",
            metadata={
                "eleve_id": eleve.pk,
                "seance_id": seance.pk,
                "cours": seance.cours.nom,
                "date": str(seance.date),
            },
        )

        # Notifier tous les parents liés à cet élève
        liens_parents = ParentEleve.objects.filter(
            eleve=eleve, actif=True
        ).select_related("parent__user")

        notif_users = [
            NotificationUser(notification=notif, user=lien.parent.user)
            for lien in liens_parents
            if hasattr(lien.parent, "user")
        ]
        if notif_users:
            NotificationUser.objects.bulk_create(notif_users, ignore_conflicts=True)
            logger.info(
                "[Signal absence] Notification envoyée à %d parent(s) pour %s",
                len(notif_users), eleve,
            )

    except Exception as exc:
        # Ne jamais bloquer la sauvegarde d'une présence
        logger.warning("[Signal absence] Erreur notification parents : %s", exc)


@receiver(post_save, sender="attendance.PresencePersonnel")
def recalculer_sommaire_paie(sender, instance, **kwargs):
    """
    Recalcule automatiquement le SommairePaiePersonnel chaque fois qu'une
    présence personnel est sauvegardée, pour maintenir les données cohérentes.
    """
    try:
        from attendance.services.personnel_presence_service import PersonnelPresenceService
        PersonnelPresenceService.recalculer_sommaire(
            instance.personnel,
            instance.date.month,
            instance.date.year,
        )
    except Exception as exc:
        logger.warning("[Signal PresencePersonnel] Erreur recalcul sommaire : %s", exc)
