from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from core.models import AnneeAcademique



class AnneeAcademiqueService:


    @staticmethod
    @transaction.atomic
    def create(**data):

        obj = AnneeAcademique(**data)

        try:

            obj.full_clean()

        except DjangoValidationError as e:

            raise ValidationError(e.message_dict)

        obj.save()

        return obj


    @staticmethod
    @transaction.atomic
    def update(instance, **data):

        for attr, value in data.items():

            setattr(instance, attr, value)


        if instance.actif:

            AnneeAcademique.objects.exclude(
                pk=instance.pk
            ).update(actif=False)


        try:

            instance.full_clean()

        except DjangoValidationError as e:

            raise ValidationError(e.message_dict)

        instance.save()

        return instance



    @staticmethod
    @transaction.atomic
    def delete(instance):

        instance.soft_delete()