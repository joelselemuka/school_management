from django.db import models
from common.models import SoftDeleteModel
from users.models import Eleve, Personnel
from core.models import AnneeAcademique

class Bus(SoftDeleteModel):
    """
    Véhicule de transport scolaire.
    """
    numero = models.CharField(max_length=20, unique=True, help_text="Numéro du bus (ex: Bus 01)")
    immatriculation = models.CharField(max_length=20, unique=True)
    capacite = models.PositiveIntegerField(help_text="Nombre total de places assises")
    modele = models.CharField(max_length=100, blank=True)
    est_operationnel = models.BooleanField(default=True)
    remarques = models.TextField(blank=True)

    class Meta:
        ordering = ["numero"]

    def __str__(self):
        return f"{self.numero} ({self.immatriculation})"


class ArretBus(SoftDeleteModel):
    """
    Point d'arrêt physique sur un itinéraire.
    """
    nom = models.CharField(max_length=100, unique=True, help_text="Ex: Rond-point Ngaba")
    adresse = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["nom"]

    def __str__(self):
        return self.nom


class Itineraire(SoftDeleteModel):
    """
    Ligne de bus affectée à un parcours spécifique.
    """
    nom = models.CharField(max_length=100, help_text="Ex: Ligne Rouge (Centre-ville)")
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE)
    description = models.TextField(blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        unique_together = ("nom", "annee_academique")
        ordering = ["nom"]

    def __str__(self):
        return f"{self.nom} - {self.annee_academique.nom}"


class ArretItineraire(models.Model):
    """
    Séquence des arrêts desservis par un itinéraire.
    """
    itineraire = models.ForeignKey(Itineraire, on_delete=models.CASCADE, related_name="arrets")
    arret = models.ForeignKey(ArretBus, on_delete=models.PROTECT)
    ordre = models.PositiveSmallIntegerField(help_text="Position dans le parcours (1, 2, 3...)")
    heure_passage_matin = models.TimeField(null=True, blank=True, help_text="Heure de ramassage")
    heure_passage_soir = models.TimeField(null=True, blank=True, help_text="Heure de dépose")

    class Meta:
        unique_together = ("itineraire", "arret")
        ordering = ["itineraire", "ordre"]

    def __str__(self):
        return f"{self.itineraire.nom} - Arrêt {self.ordre}: {self.arret.nom}"


class AffectationEleveTransport(models.Model):
    """
    Affectation d'un élève à un itinéraire de bus avec spécification
    de son arrêt de montée (matin) et descente (soir).
    """
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="transports")
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE)
    itineraire = models.ForeignKey(Itineraire, on_delete=models.PROTECT, related_name="eleves_affectes")
    
    arret_montee = models.ForeignKey(ArretItineraire, on_delete=models.PROTECT, related_name="montees")
    arret_descente = models.ForeignKey(ArretItineraire, on_delete=models.PROTECT, related_name="descentes")
    
    date_affectation = models.DateField(auto_now_add=True)
    actif = models.BooleanField(default=True)

    class Meta:
        unique_together = ("eleve", "annee_academique")

    def __str__(self):
        return f"{self.eleve} -> {self.itineraire.nom}"


class AffectationChauffeur(models.Model):
    """
    Affectation d'un chauffeur et d'un bus à un itinéraire spécifique pour
    une année académique donnée.
    """
    chauffeur = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name="affectations_transport")
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="affectations_chauffeur", null=True, blank=True)
    itineraire = models.ForeignKey(Itineraire, on_delete=models.CASCADE, related_name="chauffeurs_affectes")
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE)
    
    date_affectation = models.DateField(auto_now_add=True)
    actif = models.BooleanField(default=True, help_text="Indique si le chauffeur assure actuellement ce trajet")

    class Meta:
        unique_together = ("chauffeur", "itineraire", "annee_academique")

    def __str__(self):
        return f"{self.chauffeur.full_name} -> {self.itineraire.nom}"

