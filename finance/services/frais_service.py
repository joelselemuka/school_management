

from finance.models import Frais


class FraisService:

    @staticmethod
    def create(
        nom,
        montant,
        classe,
        annee,
        description="",
        obligatoire=True
    ):

        return Frais.objects.create(
            nom=nom,
            montant=montant,
            classe=classe,
            annee_academique=annee,
            description=description,
            obligatoire=obligatoire
        )


    @staticmethod
    def get_frais_classe(classe, annee):

        return Frais.objects.filter(
            classe=classe,
            annee_academique=annee,
            actif=True
        )


