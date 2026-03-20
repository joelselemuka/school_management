"""
Celery tasks for academics (bulletins).
"""

from celery import shared_task


@shared_task(bind=True, max_retries=3)
def generate_bulletin_task(self, eleve_id, periode_id, requested_by_id=None):
    """
    Generate a bulletin asynchronously and return its id.
    """
    from users.models import Eleve
    from core.models import Periode
    from academics.services.bulletin_service import BulletinService

    try:
        eleve = Eleve.objects.get(id=eleve_id)
        periode = Periode.objects.get(id=periode_id)
    except (Eleve.DoesNotExist, Periode.DoesNotExist):
        return {"error": "Eleve ou periode introuvable."}

    bulletin = BulletinService.generate(eleve, periode)
    return {"bulletin_id": bulletin.id}


@shared_task
def generate_period_bulletins():
    """
    Generate bulletins for the active period (if any).
    """
    from core.models import Periode
    from academics.models import Classe
    from academics.services.bulletin_service import BulletinService

    periode = Periode.get_actifs().first()
    if not periode:
        return "Aucune periode active"

    classes = Classe.objects.filter(actif=True, annee_academique=periode.annee_academique)
    total = 0
    for classe in classes:
        bulletins = BulletinService.generate_classe(classe, periode)
        total += len(bulletins)

    return f"{total} bulletins generes"
