from django.db import transaction
from rest_framework.exceptions import ValidationError
from admission.models import Inscription
from common.matricule_service import MatriculeService
from finance.services.dette_service import DetteService
from users.models import User, Eleve, Parent, ParentEleve



class InscriptionService:

    @staticmethod
    @transaction.atomic
    def create_inscription_from_data(
        eleve_data,
        guardians_data,
        classe,
        annee_academique,
        created_by=None,
        source="BUREAU"
    ):

        # ========== ELEVE USER ==========
        existing = Eleve.objects.filter(

                        nom=eleve_data["nom"],

                        postnom=eleve_data["postnom"],

                        prenom=eleve_data["prenom"],

                        date_naissance=eleve_data.get("date_naissance")

                    ).first()

        if existing:

            raise ValidationError("Eleve existe deja")
        
        matricule = MatriculeService.generate("ELEVE")

        user_eleve = User.objects.create(
            username=matricule,
            matricule=matricule,
            email=eleve_data.get("email") or None
        )
       

        eleve = Eleve.objects.create(
            user=user_eleve,
            nom=eleve_data["nom"],
            postnom=eleve_data["postnom"],
            prenom=eleve_data["prenom"],
            telephone=eleve_data.get("telephone"),
            adresse=eleve_data.get("adresse"),
            sexe=eleve_data["sexe"],
            date_naissance=eleve_data.get("date_naissance"),
            lieu_naissance=eleve_data.get("lieu_naissance"),
        )

        # ========== PARENTS ==========
        for pdata in guardians_data:

            parent_user = None

            if pdata.get("email"):
                parent_user = User.objects.filter(email=pdata["email"]).first()

            if not parent_user:
                matricule = MatriculeService.generate("PARENT")
                parent_user = User.objects.create(
                    username=matricule,
                    role="PARENT",
                    matricule=matricule,
                    email=pdata.get("email")
                )

            parent, _ = Parent.objects.get_or_create(
                user=parent_user,
                defaults={
                    "nom": pdata["nom"],
                    "postnom": pdata["postnom"],
                    "prenom": pdata["prenom"],
                    "telephone": pdata.get("telephone"),
                    "adresse": pdata.get("adresse"),
                    "sexe": pdata["sexe"],
                }
            )

            ParentEleve.objects.get_or_create(
                parent=parent,
                eleve=eleve,
                relation=pdata.get("lien")
            )

        # ========== INSCRIPTION ==========
        
        if Inscription.objects.filter(
            eleve=eleve,
            annee_academique=annee_academique
        ).exists():
            raise ValidationError("Élève déjà inscrit pour cette année.")
        
        inscription = Inscription.objects.create(
            eleve=eleve,
            classe=classe,
            annee_academique=annee_academique,
            created_by=created_by,
            source=source
        )
        DetteService.create_for_eleve(eleve)

        return inscription
