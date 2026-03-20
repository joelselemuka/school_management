import logging
from celery import shared_task
from bibliotheque.services.emprunt_service import EmpruntService

logger = logging.getLogger(__name__)

@shared_task
def verifier_retards_bibliotheque():
    """
    Tâche journalière qui applique les pénalités et notifie les retards
    aux emprunteurs, via la logique métier du service.
    """
    logger.info("Début de la vérification des retards Bibliothèque...")
    EmpruntService.verifier_retards_et_penalites()
    return "Vérification des pénalités bibliothèque terminée."
