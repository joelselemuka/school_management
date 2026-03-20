from django.db import transaction

from admission.services.admission_notification_service import AdmissionNotificationService
from admission.services.inscription_service import InscriptionService
from rest_framework.exceptions import ValidationError

class AdmissionService:

    @staticmethod
    @transaction.atomic
    def approve(application, admin_user):

        if application.status != "PENDING":
            raise ValidationError("Demande déjà traitée.")
        guardians_data = []

        for g in application.guardians.all():
            guardians_data.append({
                "nom": g.parent_nom,
                "postnom": g.parent_postnom,
                "prenom": g.parent_prenom,
                "telephone": g.parent_telephone,
                "email": g.parent_email,
                "adresse": g.parent_adresse,
                "sexe": g.parent_sexe,
            })

        eleve_data = {
            "nom": application.eleve_nom,
            "postnom": application.eleve_postnom,
            "prenom": application.eleve_prenom,
            "telephone": application.eleve_telephone,
            "email": application.eleve_email,
            "adresse": application.eleve_adresse,
            "sexe": application.eleve_sexe,
            "date_naissance": application.eleve_date_naissance,
            "lieu_naissance": application.eleve_lieu_naissance,
        }

        inscription = InscriptionService.create_inscription_from_data(
            eleve_data=eleve_data,
            guardians_data=guardians_data,
            classe=application.classe_souhaitee,
            annee_academique=application.annee_academique,
            created_by=admin_user,
            source="ONLINE"
        )

        eleve = inscription.eleve
        parents = eleve.parents.all()
        
        AdmissionNotificationService.send_admission_confirmation(
            eleve,
            parents
        )
        
        application.status = "APPROVED"
        application.is_archived = True
        application.save()
        return inscription

    @staticmethod
    def reject(application, admin_user):
        application.status = "REJECTED"
        application.is_archived = True
        application.save()
        AdmissionNotificationService.send_admission_rejected(

            application

        )
