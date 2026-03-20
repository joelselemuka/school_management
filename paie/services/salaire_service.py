"""
Service de paiement de salaire.

Responsabilités :
  - create_paiement()   : crée un PaiementSalaire et déclenche la comptabilisation
  - confirm_payment()   : confirme un paiement PENDING et comptabilise
  - apply_payment()     : appelle AccountingService + invalide les caches
"""

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

from comptabilite.services.accounting_service import AccountingService
from common.cache_utils import CacheManager, invalidate_comptabilite_reports_cache
from paie.models import PaiementSalaire
from finance.services.reference_service import ReferenceService

logger = logging.getLogger(__name__)


class SalaireService:
    """Service de paiement de salaire avec traçabilité comptable OHADA."""

    @staticmethod
    @transaction.atomic
    def create_paiement(personnel, montant, mode, mois, annee, user, note=None, annee_academique=None):
        """
        Crée un paiement de salaire.

        - Mode CASH  → statut CONFIRMED + comptabilisation immédiate
        - Mode BANK/MOBILE → statut PENDING (confirmation manuelle requise)

        Returns:
            PaiementSalaire
        """
        reference = ReferenceService.generate("SAL")

        statut = "CONFIRMED" if mode == "CASH" else "PENDING"

        salaire = PaiementSalaire.objects.create(
            reference=reference,
            personnel=personnel,
            montant=montant,
            mode=mode,
            statut=statut,
            mois=mois,
            annee=annee,
            note=note,
            annee_academique=annee_academique,
            created_by=user,
        )

        if statut == "CONFIRMED":
            SalaireService.apply_payment(salaire, user)

        logger.info(
            "PaiementSalaire créé : %s — %s — %s %02d/%d — %s",
            salaire.reference, personnel, montant, mois, annee, statut,
        )
        return salaire

    @staticmethod
    @transaction.atomic
    def confirm_payment(salaire, user):
        """
        Confirme un paiement en statut PENDING et déclenche la comptabilisation.
        """
        if salaire.statut == "CONFIRMED":
            return salaire

        if salaire.statut == "CANCELLED":
            raise ValidationError("Un paiement annulé ne peut pas être confirmé.")

        salaire.statut = "CONFIRMED"
        salaire.confirmed_by = user
        salaire.confirmed_at = timezone.now()
        salaire.save(update_fields=["statut", "confirmed_by", "confirmed_at"])

        SalaireService.apply_payment(salaire, user)
        logger.info("PaiementSalaire confirmé : %s", salaire.reference)
        return salaire

    @staticmethod
    def apply_payment(salaire, user):
        """
        Déclenche la comptabilisation OHADA du paiement de salaire.

        Débit  : compte charge salaire (662/663/664 selon fonction)
        Crédit : compte trésorerie (57 Cash / 52 Banque / 53 Mobile)

        Invalide ensuite les caches financiers.
        En cas d'échec comptable, l'erreur est loguée mais ne bloque pas.
        """
        try:
            AccountingService.create_salary_payment_transaction(salaire)
            logger.info(
                "Transaction OHADA créée pour paiement salaire %s",
                salaire.reference,
            )
        except Exception as exc:
            logger.error(
                "ERREUR comptabilisation salaire %s : %s",
                salaire.reference, exc,
            )
            # On ne bloque pas le paiement si la comptabilisation échoue
            # (l'erreur sera visible dans les logs et peut être régularisée)

        try:
            CacheManager.invalidate_pattern("salaires_list:*")
            CacheManager.invalidate_pattern("bulletins_list:*")
            CacheManager.invalidate_pattern("financial:*")
            invalidate_comptabilite_reports_cache()
        except Exception:
            pass
