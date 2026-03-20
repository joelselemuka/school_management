



from academics.services.bulletin_service import BulletinService
from django.core.exceptions import ValidationError

class BulletinBatchService:

    @staticmethod
    def generate_for_classe(classe, periode):

        eleves = classe.eleves.all()
        erreurs = []

        for eleve in eleves:
            try:
                BulletinService.generate(
                    eleve=eleve,
                    periode=periode,
                    annee_academique=periode.annee_academique
                )
            except ValidationError as e:
                erreurs.append({
                    "eleve": eleve.id,
                    "raison": str(e)
                })

        return erreurs
