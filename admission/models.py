from django.db import models

from academics.models import Classe
from common.models import SoftDeleteModel
from core.models import AnneeAcademique
from users.models import SEXE_CHOICES, Eleve, User

# Create your models here.


class Inscription(SoftDeleteModel):
    eleve = models.ForeignKey(Eleve, on_delete=models.PROTECT, related_name="inscriptions")

    classe = models.ForeignKey(Classe, on_delete=models.PROTECT, related_name="inscriptions")
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)

    date_inscription = models.DateTimeField(auto_now_add=True)

    created_by = models.ForeignKey(
        User,
        null=True,
        on_delete=models.SET_NULL,
        related_name="inscriptions_created"
    )

    source = models.CharField(
        choices=(("ONLINE","Online"),("BUREAU","Bureau")),
        max_length=10
    )

    class Meta:

        unique_together = ("eleve", "annee_academique")
        indexes = [

            models.Index(fields=["eleve"]),

            models.Index(fields=["classe"]),

            models.Index(fields=["annee_academique"]),

        ]



class AdmissionApplication(SoftDeleteModel):

    STATUS = (
        ("PENDING","Pending"),
        ("APPROVED","Approved"),
        ("REJECTED","Rejected"),
    )

    eleve_nom = models.CharField(max_length=100)
    eleve_postnom = models.CharField(max_length=100)
    eleve_prenom = models.CharField(max_length=100)
    eleve_telephone = models.CharField(max_length=30, blank=True,null=True)
    eleve_email = models.EmailField(blank=True,null=True)
    eleve_adresse = models.TextField(blank=True,null=True)
    eleve_sexe = models.CharField(max_length=10, choices=SEXE_CHOICES)
    eleve_date_naissance = models.DateField(null=True, blank=True)
    eleve_lieu_naissance = models.CharField(max_length=100, blank=True,null=True)

    classe_souhaitee = models.ForeignKey(Classe, on_delete=models.PROTECT)
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)
    
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")

    created_at = models.DateTimeField(auto_now_add=True)
    
    validated_by = models.ForeignKey(
    User,
    null=True,
    blank=True,
    on_delete=models.SET_NULL
)

    validated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=["status"]),
        ]


class AdmissionGuardian(SoftDeleteModel):

    application = models.ForeignKey(
        AdmissionApplication,
        related_name="guardians",
        on_delete=models.CASCADE
    )

    parent_nom = models.CharField(max_length=100)
    parent_postnom = models.CharField(max_length=100)
    parent_prenom = models.CharField(max_length=100)
    parent_telephone = models.CharField(max_length=30)
    parent_email = models.EmailField()
    parent_adresse = models.TextField()
    parent_sexe = models.CharField(max_length=10, choices=SEXE_CHOICES)

    lien = models.CharField(
        max_length=30,
        choices=(
            ("PERE","Père"),
            ("MERE","Mère"),
            ("TUTEUR","Tuteur"),
        )
    )




