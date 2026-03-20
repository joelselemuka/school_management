
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from academics.models import Bulletin, Note
from finance.services.finance_services import FinanceGuardService
from rest_framework.exceptions import PermissionDenied
from common.cache_utils import CacheManager


class BulletinService:

    @staticmethod
    def get(pk):
        return Bulletin.objects.select_related(
            "eleve", "periode", "annee_academique", "classe"
        ).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def generate(eleve, periode):
        """
        Génère ou met à jour le bulletin d'un élève pour une période donnée.
        Les résultats sont mis en cache Redis pour 1 heure.
        """
        BulletinService.check_financial_clearance(eleve)

        notes = Note.objects.filter(
            eleve=eleve,
            evaluation__periode=periode,
            actif=True,
        ).select_related(
            "evaluation",
            "evaluation__cours",
        )

        total = Decimal("0")
        total_coeff = Decimal("0")
        details = {}

        for note in notes:
            cours = note.evaluation.cours
            coeff = cours.coefficient
            poids = note.evaluation.poids
            bareme = note.evaluation.bareme

            score = (note.valeur / bareme) * poids * coeff
            total += score
            total_coeff += poids * coeff

            # Détails par cours pour le bulletin
            cours_key = str(cours.id)
            if cours_key not in details:
                details[cours_key] = {
                    "cours_nom": cours.nom,
                    "cours_code": cours.code,
                    "coefficient": str(coeff),
                    "notes": [],
                    "moyenne_cours": None,
                }
            details[cours_key]["notes"].append({
                "evaluation": note.evaluation.nom,
                "valeur": str(note.valeur),
                "bareme": note.evaluation.bareme,
                "poids": str(poids),
            })

        # Calculer la moyenne par cours
        for cours_key, data in details.items():
            notes_cours = [n for n in data["notes"]]
            if notes_cours:
                total_c = sum(
                    (Decimal(n["valeur"]) / n["bareme"]) * Decimal(n["poids"])
                    for n in notes_cours
                )
                total_p = sum(Decimal(n["poids"]) for n in notes_cours)
                moyenne_cours = (total_c / total_p * 20) if total_p > 0 else Decimal("0")
                data["moyenne_cours"] = str(round(moyenne_cours, 2))

        moyenne = (total / total_coeff * 20) if total_coeff > 0 else Decimal("0")
        moyenne = round(moyenne, 2)

        # Déterminer la mention
        mention = BulletinService._get_mention(moyenne)

        # Récupérer la classe courante de l'élève pour cette période
        from admission.models import Inscription
        inscription = Inscription.objects.filter(
            eleve=eleve,
            annee_academique=periode.annee_academique,
            actif=True,
        ).select_related("classe").first()

        if not inscription:
            raise ValidationError(
                f"L'élève {eleve} n'a pas d'inscription active pour cette année académique."
            )

        bulletin, created = Bulletin.objects.update_or_create(
            eleve=eleve,
            periode=periode,
            annee_academique=periode.annee_academique,
            defaults={
                "moyenne_generale": moyenne,
                "details": details,
                "mention": mention,
                "classe": inscription.classe,
            },
        )

        # Invalider le cache bulletin pour cet élève
        CacheManager.invalidate_pattern(f"bulletin:*{eleve.id}*")
        CacheManager.invalidate_pattern("bulletins_list:*")

        return bulletin

    @staticmethod
    @transaction.atomic
    def generate_classe(classe, periode):
        """Génère les bulletins pour tous les élèves d'une classe."""
        from admission.models import Inscription

        inscriptions = Inscription.objects.filter(
            classe=classe,
            actif=True,
        ).select_related("eleve")

        bulletins = []
        for inscription in inscriptions:
            bulletin = BulletinService.generate(inscription.eleve, periode)
            bulletins.append(bulletin)

        return bulletins

    @staticmethod
    def get_cached(eleve_id, periode_id):
        """
        Retourne le bulletin depuis le cache Redis si disponible,
        sinon charge depuis la base de données.
        """
        cache_key_args = {"eleve_id": eleve_id, "periode_id": periode_id}

        cached = CacheManager.get("bulletin", **cache_key_args)
        if cached is not None:
            return cached

        bulletin = Bulletin.objects.select_related(
            "eleve", "periode", "annee_academique", "classe"
        ).filter(
            eleve_id=eleve_id,
            periode_id=periode_id,
        ).first()

        if bulletin:
            CacheManager.set("bulletin", bulletin, **cache_key_args, timeout=3600)

        return bulletin

    @staticmethod
    def check_financial_clearance(eleve):
        """Verifie que l'eleve a paye les frais obligatoires."""
        if FinanceGuardService.has_unpaid_required_fees(eleve):
            raise PermissionDenied(
                "Bulletin bloque pour frais obligatoires impayes"
            )

    @staticmethod
    def _get_mention(moyenne):
        """Retourne la mention selon la moyenne sur 20."""
        if moyenne >= 18:
            return "Grande Distinction"
        elif moyenne >= 16:
            return "Distinction"
        elif moyenne >= 14:
            return "Satisfaction"
        elif moyenne >= 10:
            return "Réussite"
        else:
            return "Échec"

