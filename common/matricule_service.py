from django.db import transaction
from users.models import User
from django.db import models
from django.db import transaction
from django.db.models import Max



class MatriculeService:

    PREFIX = {
        "ELEVE": "EL",
        "PERSONNEL": "PE",
        "ADMIN": "AD",
        "PARENT": "PA",
    }

    @classmethod
    @transaction.atomic
    def generate(cls, entity_type):

        prefix = cls.PREFIX.get(entity_type)

        if not prefix:
            raise ValueError("Type invalide")

        last_matricule = (
            User.objects
            .filter(matricule__startswith=prefix)
            .select_for_update()
            .aggregate(max=models.Max("matricule"))
            .get("max")
        )

        if last_matricule:
            last_number = int(last_matricule[len(prefix):])
        else:
            last_number = 0

        new_number = last_number + 1

        return f"{prefix}{str(new_number).zfill(6)}"