from django.db import transaction
from academics.models import Evaluation


class EvaluationService:


    @staticmethod
    def get(pk):

        return Evaluation.objects.select_related(
            "cours"
        ).get(pk=pk)


    @staticmethod
    @transaction.atomic
    def create(data):

        return Evaluation.objects.create(**data)


    @staticmethod
    @transaction.atomic
    def update(pk, data):

        obj = Evaluation.objects.get(pk=pk)

        for attr, value in data.items():

            setattr(obj, attr, value)

        obj.save()

        return obj


    @staticmethod
    @transaction.atomic
    def delete(pk):

        Evaluation.objects.get(pk=pk).delete()