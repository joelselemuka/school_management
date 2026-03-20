from academics.models import Cours

from django.core.exceptions import ValidationError



class CoursService:


    @staticmethod
    def create(data):

        return Cours.objects.create(**data)


    @staticmethod
    def update(id, data):

        cours = Cours.objects.get(id=id)

        for attr, value in data.items():

            setattr(cours, attr, value)

        cours.save()

        return cours


    @staticmethod
    def delete(id):

        Cours.objects.get(id=id).soft_delete()
    
    
    @staticmethod   
    def assign_to_classe(classe, personnel, matiere):

        return Cours.objects.create(
            classe=classe,
            personnel=personnel,
            matiere=matiere,
            annee_academique=classe.annee_academique
        )


