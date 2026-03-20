"""
Service de génération et gestion des bulletins de salaire.

Workflow attendu :
  1. generer_bulletin()        → statut BROUILLON (calcul automatique)
  2. valider_bulletin()        → statut VALIDE
  3. payer_bulletin()          → statut PAYE + PaiementSalaire + Transaction OHADA

Actions complémentaires :
  - generer_bulletins_masse()  → génération pour tous les contrats actifs d'un mois
"""

from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
import logging

from paie.models import BulletinSalaire

logger = logging.getLogger(__name__)


class BulletinSalaireService:
    """Service de gestion du cycle de vie des bulletins de salaire."""

    @staticmethod
    @transaction.atomic
    def generer_bulletin(
        contrat,
        mois,
        annee,
        user,
        nb_jours_absence=0,
        nb_heures_supplementaires=Decimal("0"),
        prime_motivation=None,
        autres_primes=Decimal("0"),
        note_primes=None,
        autres_retenues=Decimal("0"),
        note_retenues=None,
    ):
        """
        Génère un bulletin de salaire mensuel pour un personnel.
        Le salaire net est calculé automatiquement par le modèle.

        Raises:
            ValidationError si un bulletin existe déjà pour ce mois/année,
            ou si le contrat n'est pas actif ou est expiré.
        """
        # Unicité : un seul bulletin par personnel/mois/année
        if BulletinSalaire.objects.filter(
            personnel=contrat.personnel, mois=mois, annee=annee
        ).exists():
            raise ValidationError(
                f"Un bulletin de salaire existe déjà pour {contrat.personnel} "
                f"en {mois:02d}/{annee}."
            )

        if contrat.statut != "ACTIF":
            raise ValidationError(
                f"Le contrat {contrat.id} n'est pas actif (statut: {contrat.statut})."
            )

        # Vérifier si le contrat est effectivement expiré (date_fin dépassée)
        if contrat.is_expired:
            raise ValidationError(
                f"Le contrat {contrat.id} est expiré (date de fin : {contrat.date_fin}). "
                f"Veuillez renouveler le contrat avant de générer un bulletin."
            )

        prime = prime_motivation if prime_motivation is not None else contrat.prime_motivation

        bulletin = BulletinSalaire(
            contrat=contrat,
            personnel=contrat.personnel,
            mois=mois,
            annee=annee,
            salaire_base=contrat.salaire_base,
            nb_jours_absence=nb_jours_absence,
            nb_heures_supplementaires=nb_heures_supplementaires,
            prime_motivation=prime,
            autres_primes=autres_primes,
            note_primes=note_primes,
            autres_retenues=autres_retenues,
            note_retenues=note_retenues,
            statut="BROUILLON",
            created_by=user,
        )
        # Le save() appelle recalculer() automatiquement via BulletinSalaire.save()
        bulletin.save()

        logger.info(
            "Bulletin généré : %s %02d/%d — net=%s",
            contrat.personnel, mois, annee, bulletin.salaire_net,
        )
        return bulletin

    @staticmethod
    @transaction.atomic
    def valider_bulletin(bulletin, user):
        """
        Valide un bulletin en statut BROUILLON.
        Un bulletin validé peut être payé.
        """
        if bulletin.statut != "BROUILLON":
            raise ValidationError(
                f"Seuls les bulletins brouillons peuvent être validés "
                f"(statut actuel : {bulletin.statut})."
            )
        bulletin.statut = "VALIDE"
        bulletin.save(update_fields=["statut", "updated_at"])
        logger.info("Bulletin validé : %s", bulletin)
        return bulletin

    @staticmethod
    @transaction.atomic
    def payer_bulletin(bulletin, mode, user, note=None, annee_academique=None):
        """
        Déclenche le paiement d'un bulletin VALIDE (ou BROUILLON en urgence).

        Crée un PaiementSalaire, le lie au bulletin, et déclenche
        automatiquement la transaction comptable OHADA via SalaireService.

        Returns:
            tuple: (BulletinSalaire, PaiementSalaire)
        """
        if bulletin.statut == "PAYE":
            raise ValidationError("Ce bulletin est déjà payé.")

        if bulletin.paiement is not None:
            raise ValidationError("Ce bulletin est déjà lié à un paiement.")

        # Vérifier que le contrat du bulletin n'est pas expiré
        contrat = bulletin.contrat
        if contrat.is_expired:
            raise ValidationError(
                f"Impossible de payer ce bulletin : le contrat {contrat.id} est expiré "
                f"(date de fin : {contrat.date_fin}). "
                f"Veuillez renouveler le contrat avant de procéder au paiement."
            )

        from paie.services.salaire_service import SalaireService

        paiement = SalaireService.create_paiement(
            personnel=bulletin.personnel,
            montant=bulletin.salaire_net,
            mode=mode,
            mois=bulletin.mois,
            annee=bulletin.annee,
            user=user,
            note=note,
            annee_academique=annee_academique,
        )

        bulletin.paiement = paiement
        bulletin.statut = "PAYE"
        bulletin.save(update_fields=["paiement", "statut", "updated_at"])

        logger.info(
            "Bulletin payé : %s — réf paiement : %s — montant : %s",
            bulletin, paiement.reference, paiement.montant,
        )
        return bulletin, paiement

    @staticmethod
    @transaction.atomic
    def generer_bulletins_masse(contrats_data, mois, annee, user):
        """
        Génère les bulletins de salaire en masse pour une liste de contrats.

        Args:
            contrats_data : liste de dicts {contrat, nb_jours_absence,
                            nb_heures_supplementaires, prime_motivation,
                            autres_primes, note_primes, autres_retenues, note_retenues}
            mois          : mois concerné (1-12)
            annee         : année concernée
            user          : utilisateur créateur

        Returns:
            dict { created: [...], skipped: [...], errors: [...] }
        """
        results = {"created": [], "skipped": [], "errors": []}

        for data in contrats_data:
            contrat = data.get("contrat")
            try:
                if BulletinSalaire.objects.filter(
                    personnel=contrat.personnel, mois=mois, annee=annee
                ).exists():
                    results["skipped"].append({
                        "personnel": str(contrat.personnel),
                        "raison": f"Bulletin déjà existant pour {mois:02d}/{annee}",
                    })
                    continue

                bulletin = BulletinSalaireService.generer_bulletin(
                    contrat=contrat,
                    mois=mois,
                    annee=annee,
                    user=user,
                    nb_jours_absence=data.get("nb_jours_absence", 0),
                    nb_heures_supplementaires=data.get("nb_heures_supplementaires", Decimal("0")),
                    prime_motivation=data.get("prime_motivation"),
                    autres_primes=data.get("autres_primes", Decimal("0")),
                    note_primes=data.get("note_primes"),
                    autres_retenues=data.get("autres_retenues", Decimal("0")),
                    note_retenues=data.get("note_retenues"),
                )
                results["created"].append({
                    "bulletin_id": bulletin.id,
                    "personnel": str(contrat.personnel),
                    "salaire_net": float(bulletin.salaire_net),
                })

            except Exception as exc:
                results["errors"].append({
                    "personnel": str(contrat.personnel) if contrat else "Inconnu",
                    "erreur": str(exc),
                })

        logger.info(
            "Génération masse %02d/%d — créés: %d, ignorés: %d, erreurs: %d",
            mois, annee,
            len(results["created"]), len(results["skipped"]), len(results["errors"]),
        )
        return results
