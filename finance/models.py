from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings
from decimal import Decimal

from academics.models import Classe
from core.models import AnneeAcademique
from users.models import Eleve, Personnel


class CompteEleve(models.Model):
    eleve = models.ForeignKey(
        Eleve,
        on_delete=models.CASCADE,
        related_name="comptes"
    )

    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.CASCADE
    )

    total_du = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("eleve", "annee_academique")

    @property
    def solde(self):
        return self.total_du - self.total_paye


class Frais(models.Model):
    nom = models.CharField(max_length=255)
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT)
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date_limite = models.DateField()
    obligatoire = models.BooleanField(default=True)
    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("nom", "classe", "annee_academique")

       
class DetteEleve(models.Model):
    eleve = models.ForeignKey("users.Eleve", on_delete=models.CASCADE)
    frais = models.ForeignKey(Frais, on_delete=models.PROTECT)

    montant_initial = models.DecimalField(max_digits=12, decimal_places=2)
    montant_reduit = models.DecimalField(max_digits=12, decimal_places=2)

    montant_paye = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    montant_du = models.DecimalField(max_digits=12, decimal_places=2)

    statut = models.CharField(
        max_length=20,
        choices=[
            ("IMPAYE", "Impayé"),
            ("PARTIEL", "Partiel"),
            ("PAYE", "Payé"),
        ],
        default="IMPAYE",
    )

    last_payment_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("eleve", "frais")
        indexes = [
            models.Index(fields=["eleve", "statut"]),
        ]


class Paiement(models.Model):
    reference = models.CharField(max_length=50, unique=True)

    eleve = models.ForeignKey("users.Eleve", on_delete=models.PROTECT)

    montant = models.DecimalField(max_digits=12, decimal_places=2)

    MODE = [
        ("CASH", "Cash"),
        ("BANK", "Banque"),
        ("MOBILE", "Mobile Money"),
    ]

    STATUS = [
        ("PENDING", "En attente"),
        ("CONFIRMED", "Confirmé"),
        ("CANCELLED", "Annulé"),
    ]

    mode = models.CharField(max_length=10, choices=MODE)
    statut = models.CharField(max_length=10, choices=STATUS, default="PENDING")

    transaction_id_externe = models.CharField(
        max_length=120,
        null=True,
        blank=True
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="confirmed_payments",
        on_delete=models.PROTECT
    )

    confirmed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["eleve", "statut"]),
            models.Index(fields=["created_at"]),
        ]


class PaiementAllocation(models.Model):
    paiement = models.ForeignKey(Paiement, related_name="allocations", on_delete=models.CASCADE)
    dette = models.ForeignKey(DetteEleve, on_delete=models.PROTECT)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    
    class Meta:
        indexes = [
            models.Index(fields=["paiement"]),
            models.Index(fields=["dette"]),
        ]


class Facture(models.Model):
    numero = models.CharField(max_length=50, unique=True)

    paiement = models.OneToOneField(
        Paiement,
        on_delete=models.PROTECT,
        related_name="facture"
    )

    eleve = models.ForeignKey("users.Eleve", on_delete=models.PROTECT)

    montant = models.DecimalField(max_digits=10, decimal_places=2)

    pdf = models.FileField(upload_to="factures/", null=True, blank=True)

    date_emission = models.DateTimeField()

    statut = models.CharField(
        max_length=20,
        choices=[
            ("PAID", "Payé"),
            ("CANCELLED", "Annulé"),
        ],
    )

    created_at = models.DateTimeField(auto_now_add=True)


