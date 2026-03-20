"""
Service de gestion du personnel.
"""

import secrets
import logging
from django.db import transaction
from django.core.exceptions import ValidationError

from common.matricule_service import MatriculeService
from users.models import User, Personnel

logger = logging.getLogger(__name__)


class PersonnelService:
    """
    Service pour la gestion du personnel.
    """

    @staticmethod
    @transaction.atomic
    def create(data, user=None):
        """
        Crée un nouveau membre du personnel avec son compte utilisateur
        et son contrat de travail par défaut.

        Prérequis OBLIGATOIRE : une configuration École (core.Ecole) doit
        exister et être active. Si ce n'est pas le cas, une ValidationError
        est levée AVANT toute autre action.

        Args:
            data: dict contenant les informations du personnel
            user: utilisateur créateur (pour le contrat)

        Returns:
            tuple: (Personnel, generated_password)
        """
        # ── 1. Vérifier la configuration de l'école (prérequis strict) ─────────
        from core.models import Ecole
        ecole = Ecole.get_configuration()  # Lève ValidationError si absente

        # ── 2. Générer le matricule et le mot de passe ───────────────────────────
        matricule = MatriculeService.generate("PERSONNEL")

        password = data.get("password")
        if not password:
            password = secrets.token_urlsafe(10)

        # ── 3. Vérifier l'unicité de l'e-mail ───────────────────────────────────
        email = data.get("email")
        if email and User.objects.filter(email=email).exists():
            raise ValueError("Email déjà utilisé")

        # ── 4. Créer l'utilisateur ───────────────────────────────────────────────
        user_obj = User.objects.create_user(
            username=matricule,
            matricule=matricule,
            email=email,
            password=password,
            is_staff=True,
        )

        # ── 5. Créer le profil personnel ─────────────────────────────────────────
        personnel = Personnel.objects.create(
            user=user_obj,
            nom=data["nom"],
            postnom=data["postnom"],
            prenom=data["prenom"],
            specialite=data.get("specialite", ""),
            telephone=data.get("telephone"),
            date_naissance=data.get("date_naissance"),
            lieu_naissance=data.get("lieu_naissance"),
            adresse=data.get("adresse"),
            sexe=data.get("sexe"),
            fonction=data.get("fonction", "enseignant"),
        )

        # ── 6. Créer le contrat de travail par défaut ────────────────────────────
        #  Le créateur du contrat est soit l'utilisateur passé en paramètre,
        #  soit l'utilisateur système (superadmin), soit on l'ignore si absent.
        contrat_user = user or user_obj  # Fallback vers le compte lui-même

        from finance.services.contrat_service import ContratService
        ContratService.creer_contrat_defaut(
            personnel=personnel,
            ecole=ecole,
            user=contrat_user,
            salaire_base=data.get("salaire_base", 0),
            poste=data.get("poste") or data.get("fonction", "enseignant"),
            date_debut=data.get("date_debut_contrat"),
        )

        logger.info(
            "Personnel créé avec contrat par défaut : %s (matricule: %s)",
            str(personnel),
            matricule,
        )

        return personnel, password

    @staticmethod
    @transaction.atomic
    def update(personnel_id, data):
        """Modifie les informations d'un membre du personnel."""
        personnel = (
            Personnel.objects
            .select_related("user")
            .get(id=personnel_id)
        )

        user = personnel.user

        # Mise à jour des champs personnel
        personnel.nom = data.get("nom", personnel.nom)
        personnel.postnom = data.get("postnom", personnel.postnom)
        personnel.prenom = data.get("prenom", personnel.prenom)
        personnel.telephone = data.get("telephone", personnel.telephone)
        personnel.fonction = data.get("fonction", personnel.fonction)
        personnel.specialite = data.get("specialite", personnel.specialite)
        personnel.date_naissance = data.get("date_naissance", personnel.date_naissance)
        personnel.lieu_naissance = data.get("lieu_naissance", personnel.lieu_naissance)
        personnel.sexe = data.get("sexe", personnel.sexe)
        personnel.adresse = data.get("adresse", personnel.adresse)

        personnel.save()

        # Mise à jour de l'e-mail
        email = data.get("email")
        if email:
            if User.objects.filter(email=email).exclude(id=user.id).exists():
                raise ValueError("Email déjà utilisé")
            user.email = email
            user.save()

        return personnel

    @staticmethod
    @transaction.atomic
    def delete(personnel_id):
        """Désactive un membre du personnel (soft delete)."""
        personnel = Personnel.objects.select_related("user").get(id=personnel_id)
        user = personnel.user

        personnel.delete()  # soft delete via SoftDeleteModel

        user.is_active = False
        user.save()