from django.db import transaction
from django.db.models import F
from django.utils import timezone

from comptabilite.services.accounting_service import AccountingService
from finance.models import  DetteEleve, Paiement, PaiementAllocation

from finance.services.reference_service import ReferenceService
from communication.services.notification_service import NotificationService
from users.models import ParentEleve
from common.role_services import RoleService
from rest_framework.exceptions import PermissionDenied



        

class PaiementService:

    @staticmethod
    @transaction.atomic
    def create_paiement(eleve, montant, mode, user):

        reference = ReferenceService.generate("PAY")

        statut = "CONFIRMED" if mode == "CASH" else "PENDING"

        if RoleService.is_parent(user):

            if not ParentEleve.objects.filter(
                parent=user.parent_profile,
                eleve=eleve
            ).exists():

                raise PermissionDenied("Vous ne pouvez pas payer pour cet élève")

        paiement = Paiement.objects.create(
            reference=reference,
            eleve=eleve,
            montant=montant,
            mode=mode,
            statut=statut,
            created_by=user
        )

        if statut == "CONFIRMED":
            PaiementService.apply_payment(paiement)

        return paiement

    @staticmethod
    @transaction.atomic
    def process_payment(paiement):
        """
        Traite un paiement crÃ©Ã© via API.
        - CASH: confirme immÃ©diatement et applique le paiement.
        - Autres modes: reste en PENDING.
        """
        if paiement.mode == "CASH" and paiement.statut != "CONFIRMED":
            paiement.statut = "CONFIRMED"
            paiement.confirmed_by = paiement.created_by
            paiement.confirmed_at = timezone.now()
            paiement.save(update_fields=["statut", "confirmed_by", "confirmed_at"])
            PaiementService.apply_payment(paiement)

        return paiement

    @staticmethod
    @transaction.atomic
    def confirm_payment(paiement, user):
        """Confirme manuellement un paiement en attente."""
        if paiement.statut == "CONFIRMED":
            return paiement

        paiement.statut = "CONFIRMED"
        paiement.confirmed_by = user
        paiement.confirmed_at = timezone.now()
        paiement.save(update_fields=["statut", "confirmed_by", "confirmed_at"])

        PaiementService.apply_payment(paiement)
        return paiement

    @staticmethod
    def apply_payment(paiement):

        reste = paiement.montant

        dettes = DetteEleve.objects.filter(
            eleve=paiement.eleve,
            statut__in=["IMPAYE", "PARTIEL"]
        ).order_by("created_at")

        for dette in dettes:

            if reste <= 0:
                break

            montant_a_payer = min(reste, dette.montant_du)

            dette.montant_paye += montant_a_payer
            dette.montant_du -= montant_a_payer

            if dette.montant_du == 0:
                dette.statut = "PAYE"
            else:
                dette.statut = "PARTIEL"

            dette.save()

            PaiementAllocation.objects.create(
                paiement=paiement,
                dette=dette,
                montant=montant_a_payer
            )

            reste -= montant_a_payer

        AccountingService.create_payment_transaction(paiement)
        NotificationService.notify_payment(paiement)

        try:
            from common.cache_utils import CacheManager
            CacheManager.invalidate_pattern("paiements_list:*")
            CacheManager.invalidate_pattern("dettes_list:*")
            CacheManager.invalidate_pattern("comptes_list:*")
            CacheManager.invalidate_pattern("factures_list:*")
        except Exception:
            pass

        # Facture + email en asynchrone
        try:
            from finance.tasks import generate_and_send_facture
            generate_and_send_facture.delay(paiement.id)
        except Exception:
            # Ne pas bloquer la confirmation si Celery est indisponible
            pass
