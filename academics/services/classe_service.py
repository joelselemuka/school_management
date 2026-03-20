

from django.core.exceptions import ValidationError

from academics.models import Classe



# academics/services/classe_service.py

from django.db import transaction
from academics.models import Classe


class ClasseService:


    @staticmethod
    @transaction.atomic
    def create(data):

        return Classe.objects.create(**data)


    @staticmethod
    @transaction.atomic
    def update(classe_id, data):

        classe = Classe.objects.get(id=classe_id)

        for attr, value in data.items():

            setattr(classe, attr, value)

        classe.save()

        return classe

    
    
    
    @staticmethod
    def list():

        return Classe.objects.select_related(
            "annee_academique",
            "titulaire"
        )


    @staticmethod
    def get(classe_id):

        return Classe.objects.select_related(
            "annee_academique",
            "titulaire"
        ).get(id=classe_id)

    
    
    
    

    @staticmethod
    @transaction.atomic
    def delete(classe_id):

        classe = Classe.objects.get(id=classe_id)

        classe.soft_delete()