"""
Service de gestion des contrats d'embauche.

Responsabilités :
  - creer_contrat()             : créer un contrat explicite (via API DRH)
  - creer_contrat_defaut()      : créer le contrat initial à l'embauche
  - modifier_contrat()          : modifier les champs financiers d'un contrat
  - resilier_contrat()          : mettre fin à un contrat actif
  - get_contrat_actif()         : récupérer le contrat en cours d'un personnel
  - simuler_salaire()           : calculer un net prévisionnel sans bulletin
"""

from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging

from paie.models import ContratEmploye, RenouvellementContrat

logger = logging.getLogger(__name__)


class ContratService:
    """Service de gestion des contrats d'embauche du personnel."""

    # ── Renouvellement ───────────────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def renouveler_contrat(ancien_contrat, user, date_debut, date_fin=None,
                           salaire_base=None, prime_motivation=None,
                           taux_retenue_absence=None, taux_heure_supplementaire=None,
                           nb_jours_ouvrable=None, observations=None, motif=None):
        """
        Renouvelle un contrat existant.

        Workflow :
          1. Vérifie que l'ancien contrat est renouvelable (ACTIF ou effectivement expiré)
          2. Passe l'ancien contrat au statut RENOUVELE
          3. Crée un nouveau contrat ACTIF (reprend les valeurs non fournies)
          4. Crée un enregistrement RenouvellementContrat

        Returns:
            tuple: (nouveau_contrat, renouvellement)
        """
        statut_effectif = ancien_contrat.statut_effectif

        if statut_effectif not in ("ACTIF", "EXPIRE"):
            raise ValidationError(
                f"Seuls les contrats ACTIF ou EXPIRE peuvent être renouvelés "
                f"(statut actuel : {ancien_contrat.statut}, "
                f"statut effectif : {statut_effectif})."
            )

        type_contrat = ancien_contrat.type_contrat
        if type_contrat in ("CDD", "STAGE", "INTERIM") and not date_fin:
            raise ValidationError(
                f"La date de fin est obligatoire pour un contrat {type_contrat}."
            )

        if date_fin and date_fin <= date_debut:
            raise ValidationError(
                "La date de fin doit être postérieure à la date de début."
            )

        # Passer l'ancien contrat au statut RENOUVELE
        ancien_contrat.statut = "RENOUVELE"
        ancien_contrat.save(update_fields=["statut", "updated_at"])

        # Créer le nouveau contrat avec les nouvelles conditions
        nouveau_contrat = ContratEmploye.objects.create(
            personnel=ancien_contrat.personnel,
            type_contrat=ancien_contrat.type_contrat,
            poste=ancien_contrat.poste,
            date_debut=date_debut,
            date_fin=date_fin,
            salaire_base=salaire_base if salaire_base is not None else ancien_contrat.salaire_base,
            nb_jours_ouvrable=nb_jours_ouvrable if nb_jours_ouvrable is not None else ancien_contrat.nb_jours_ouvrable,
            taux_retenue_absence=taux_retenue_absence if taux_retenue_absence is not None else ancien_contrat.taux_retenue_absence,
            taux_heure_supplementaire=taux_heure_supplementaire if taux_heure_supplementaire is not None else ancien_contrat.taux_heure_supplementaire,
            prime_motivation=prime_motivation if prime_motivation is not None else ancien_contrat.prime_motivation,
            observations=observations or f"Renouvellement du contrat #{ancien_contrat.id}",
            statut="ACTIF",
            created_by=user,
        )

        # Tracer le renouvellement
        renouvellement = RenouvellementContrat.objects.create(
            ancien_contrat=ancien_contrat,
            nouveau_contrat=nouveau_contrat,
            date_renouvellement=date_debut,
            motif=motif or "",
            created_by=user,
        )

        logger.info(
            "Contrat renouvelé : %s → %s (personnel: %s, par: %s)",
            ancien_contrat.id, nouveau_contrat.id, ancien_contrat.personnel, user,
        )
        return nouveau_contrat, renouvellement

    @staticmethod
    @transaction.atomic
    def creer_contrat(
        personnel,
        type_contrat,
        poste,
        date_debut,
        salaire_base,
        user,
        date_fin=None,
        nb_jours_ouvrable=26,
        taux_retenue_absence=Decimal("100.00"),
        taux_heure_supplementaire=Decimal("0"),
        prime_motivation=Decimal("0"),
        observations=None,
    ):
        """
        Crée un nouveau contrat d'embauche pour un personnel.
        Refuse si un contrat ACTIF existe déjà.
        """
        if ContratEmploye.objects.filter(personnel=personnel, statut="ACTIF").exists():
            raise ValidationError(
                f"Le personnel {personnel} possède déjà un contrat actif. "
                "Veuillez le résilier ou le suspendre avant d'en créer un nouveau."
            )

        contrat = ContratEmploye.objects.create(
            personnel=personnel,
            type_contrat=type_contrat,
            poste=poste,
            date_debut=date_debut,
            date_fin=date_fin,
            salaire_base=salaire_base,
            nb_jours_ouvrable=nb_jours_ouvrable,
            taux_retenue_absence=taux_retenue_absence,
            taux_heure_supplementaire=taux_heure_supplementaire,
            prime_motivation=prime_motivation,
            observations=observations,
            statut="ACTIF",
            created_by=user,
        )
        logger.info("Contrat créé : %s", contrat)
        return contrat

    @staticmethod
    @transaction.atomic
    def creer_contrat_defaut(personnel, user, ecole=None, salaire_base=0, poste=None, date_debut=None):
        """
        Crée un contrat CDI par défaut pour un personnel nouvellement embauché.
        Utilise les taux globaux de l'école si fournis, sinon des valeurs standard.

        Ce contrat est un point de départ : le DRH peut le compléter via l'API.

        Retourne None si un contrat actif existe déjà (idempotent).
        """
        if ContratEmploye.objects.filter(personnel=personnel, statut="ACTIF").exists():
            logger.warning("Personnel %s a déjà un contrat actif — ignoré.", personnel)
            return None

        if date_debut is None:
            date_debut = timezone.now().date()

        # Taux depuis la config de l'école (ou valeurs par défaut)
        taux_retenue = Decimal("100.00")
        taux_heures_sup = Decimal("0")
        if ecole is not None:
            taux_retenue = ecole.taux_retenue_absence_defaut
            taux_heures_sup = ecole.taux_heure_supplementaire_defaut

        poste_map = {
            "enseignant": "Enseignant",
            "comptable": "Comptable",
            "secretaire": "Secrétaire",
            "admin": "Administrateur",
            "drh": "DRH",
            "agent_entretien": "Agent d'entretien",
        }
        intitule_poste = poste or poste_map.get(personnel.fonction, personnel.fonction.capitalize())

        contrat = ContratEmploye.objects.create(
            personnel=personnel,
            type_contrat="CDI",
            poste=intitule_poste,
            date_debut=date_debut,
            date_fin=None,
            salaire_base=Decimal(str(salaire_base)),
            nb_jours_ouvrable=26,
            taux_retenue_absence=taux_retenue,
            taux_heure_supplementaire=taux_heures_sup,
            prime_motivation=Decimal("0"),
            statut="ACTIF",
            observations=(
                "Contrat créé automatiquement à l'embauche. "
                "Veuillez compléter le salaire de base et les paramètres via l'API."
            ),
            created_by=user,
        )
        logger.info("Contrat par défaut créé pour %s (id: %d, poste: %s)", personnel, contrat.id, intitule_poste)
        return contrat

    @staticmethod
    @transaction.atomic
    def modifier_contrat(contrat, user, **kwargs):
        """Modifie les champs financiers autorisés d'un contrat existant."""
        champs_modifiables = [
            "poste", "salaire_base", "nb_jours_ouvrable",
            "taux_retenue_absence", "taux_heure_supplementaire",
            "prime_motivation", "observations", "date_fin", "statut",
        ]
        for champ, valeur in kwargs.items():
            if champ in champs_modifiables:
                setattr(contrat, champ, valeur)
        contrat.save()
        return contrat

    @staticmethod
    @transaction.atomic
    def resilier_contrat(contrat, user):
        """Résilie un contrat actif ou suspendu."""
        if contrat.statut == "RESILIE":
            raise ValidationError("Ce contrat est déjà résilié.")
        contrat.statut = "RESILIE"
        contrat.save(update_fields=["statut", "updated_at"])
        logger.info("Contrat résilié : %s (par %s)", contrat, user)
        return contrat

    @staticmethod
    def get_contrat_actif(personnel):
        """Retourne le contrat actif d'un personnel, ou None."""
        return ContratEmploye.objects.filter(personnel=personnel, statut="ACTIF").first()

    @staticmethod
    def simuler_salaire(
        contrat,
        nb_jours_absence=0,
        nb_heures_supplementaires=Decimal("0"),
        prime_motivation=None,
        autres_primes=Decimal("0"),
        autres_retenues=Decimal("0"),
    ):
        """
        Simule le calcul du salaire net sans créer de bulletin.
        Retourne un dictionnaire avec le détail complet du calcul.
        """
        salaire_base = contrat.salaire_base
        prime = prime_motivation if prime_motivation is not None else contrat.prime_motivation

        retenue_absence = contrat.calculer_retenue_absence(nb_jours_absence)
        montant_heures_sup = contrat.calculer_montant_heures_sup(nb_heures_supplementaires)

        total_gains = salaire_base + montant_heures_sup + prime + autres_primes
        total_retenues = retenue_absence + autres_retenues
        salaire_net = max(total_gains - total_retenues, Decimal("0"))

        return {
            "contrat_id": contrat.id,
            "personnel": str(contrat.personnel),
            "poste": contrat.poste,
            "salaire_base": float(salaire_base),
            "salaire_journalier": float(contrat.salaire_journalier),
            "nb_jours_ouvrable": contrat.nb_jours_ouvrable,
            "taux_retenue_absence": float(contrat.taux_retenue_absence),
            "nb_jours_absence": nb_jours_absence,
            "retenue_absence": float(retenue_absence),
            "taux_heure_supplementaire": float(contrat.taux_heure_supplementaire),
            "nb_heures_supplementaires": float(nb_heures_supplementaires),
            "montant_heures_sup": float(montant_heures_sup),
            "prime_motivation": float(prime),
            "autres_primes": float(autres_primes),
            "autres_retenues": float(autres_retenues),
            "total_gains": float(total_gains),
            "total_retenues": float(total_retenues),
            "salaire_net": float(salaire_net),
        }
