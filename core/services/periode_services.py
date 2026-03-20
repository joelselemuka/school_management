

from core.models import Periode
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError

from django.db import transaction




class PeriodeService:


    @staticmethod
    @transaction.atomic
    def create(**data):

        obj = Periode(**data)

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
