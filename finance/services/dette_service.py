from decimal import Decimal
from django.db import transaction
from django.db.models import Q

from finance.models import DetteEleve
from finance.services.frais_service import FraisService
from users.models import Eleve

from django.db import transaction, models
from django.db.models import F


from finance.services.discount_service import DiscountService



class DetteService:

    @staticmethod
    @transaction.atomic
    def create_for_frais(frais):

        inscriptions = frais.classe.inscriptions.filter(
            annee_academique=frais.annee_academique
        )

        for ins in inscriptions:
            eleve = ins.eleve

            if DetteEleve.objects.filter(eleve=eleve, frais=frais).exists():
                continue

            montant_reduit = DiscountService.calculate(eleve, frais.montant)

            DetteEleve.objects.create(
                eleve=eleve,
                frais=frais,
                montant_initial=frais.montant,
                montant_reduit=montant_reduit,
                montant_du=montant_reduit
            )
