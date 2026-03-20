import uuid
from django.db import models
from django.conf import settings
from common.models import SoftDeleteModel

class Livre(SoftDeleteModel):
    """
    Fiche de référence d'un livre (oeuvre).
    Un livre peut avoir plusieurs exemplaires physiques.
    """
    titre = models.CharField(max_length=255)
    auteur = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, blank=True, null=True, unique=True)
    categorie = models.CharField(max_length=100, blank=True)
    langue = models.CharField(max_length=50, default="Français")
    date_publication = models.DateField(blank=True, null=True)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to="bibliotheque/livres/", blank=True, null=True)

    class Meta:
        ordering = ["titre"]
        indexes = [
            models.Index(fields=["titre"]),
            models.Index(fields=["auteur"]),
            models.Index(fields=["isbn"]),
        ]

    def __str__(self):
        return f"{self.titre} - {self.auteur}"

    @property
    def exemplaires_disponibles(self):
        return self.exemplaires.filter(est_disponible=True, actif=True).count()


ETATS_EXEMPLAIRE = [
    ("NEUF", "Neuf"),
    ("BON", "Bon état"),
    ("USE", "Usé"),
    ("ABIME", "Abîmé"),
    ("PERDU", "Perdu"),
]


class Exemplaire(SoftDeleteModel):
    """
    Copie physique spécifique d'un livre.
    C'est ce qui est réellement emprunté par les utilisateurs.
    """
    livre = models.ForeignKey(Livre, on_delete=models.CASCADE, related_name="exemplaires")
    code_barre = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    etat = models.CharField(max_length=20, choices=ETATS_EXEMPLAIRE, default="NEUF")
    est_disponible = models.BooleanField(default=True)
    date_acquisition = models.DateField(auto_now_add=True)
    prix_acquisition = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    remarque = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["code_barre"]),
            models.Index(fields=["est_disponible"]),
        ]

    def __str__(self):
        return f"{self.livre.titre} (Ref: {self.code_barre})"


STATUTS_EMPRUNT = [
    ("EN_COURS", "En cours"),
    ("EN_RETARD", "En retard"),
    ("RETOURNE", "Retourné"),
    ("PERDU", "Déclaré perdu"),
]


class Emprunt(models.Model):
    """
    Enregistrement d'un emprunt d'un exemplaire par un utilisateur.
    """
    exemplaire = models.ForeignKey(Exemplaire, on_delete=models.PROTECT, related_name="historique_emprunts")
    emprunteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="emprunts_bibliotheque")
    
    date_emprunt = models.DateField(auto_now_add=True)
    date_retour_prevue = models.DateField()
    date_retour_effective = models.DateField(null=True, blank=True)
    
    statut = models.CharField(max_length=20, choices=STATUTS_EMPRUNT, default="EN_COURS")
    
    enregistre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="emprunts_enregistres", null=True)
    retour_enregistre_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="retours_enregistres", null=True, blank=True)
    
    remarque_emprunt = models.TextField(blank=True)
    remarque_retour = models.TextField(blank=True)
    
    # Suivi des pénalités
    montant_penalite = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalite_payee = models.BooleanField(default=False)

    class Meta:
        ordering = ["-date_emprunt"]
        indexes = [
            models.Index(fields=["statut"]),
            models.Index(fields=["date_emprunt"]),
            models.Index(fields=["date_retour_prevue"]),
        ]

    def __str__(self):
        return f"{self.exemplaire.livre.titre} emprunté par {self.emprunteur}"

    @property
    def est_en_retard(self):
        from django.utils import timezone
        if self.statut in ["RETOURNE", "PERDU"]:
            return False
        return timezone.now().date() > self.date_retour_prevue


MODES_PAIEMENT = [("CASH", "Cash"), ("MOBILE", "Mobile Money"), ("BANK", "Virement Bancaire")]


class PaiementAmende(models.Model):
    """
    Paiement d'une amende pour retard ou perte de livre.
    """
    emprunt = models.ForeignKey(Emprunt, on_delete=models.PROTECT, related_name="amendes")
    reference = models.CharField(max_length=50, unique=True, blank=True) # généré auto
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    mode = models.CharField(max_length=20, choices=MODES_PAIEMENT, default="CASH")
    motif = models.CharField(max_length=255, default="Retard de retour")
    
    date_paiement = models.DateTimeField(auto_now_add=True)
    percu_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        ordering = ["-date_paiement"]

    def __str__(self):
        return f"Amende {self.montant} pour {self.emprunt.emprunteur}"


class Inventaire(models.Model):
    """
    Campagne d'inventaire physique de la bibliothèque.
    """
    date_debut = models.DateField(auto_now_add=True)
    date_cloture = models.DateField(null=True, blank=True)
    nom = models.CharField(max_length=255, help_text="Ex: Inventaire Annuel 2026")
    en_cours = models.BooleanField(default=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    observations = models.TextField(blank=True)

    class Meta:
        ordering = ["-date_debut"]

    def __str__(self):
        return self.nom


class LigneInventaire(models.Model):
    """
    Résultat pointé pour un exemplaire lors d'un inventaire.
    """
    inventaire = models.ForeignKey(Inventaire, on_delete=models.CASCADE, related_name="lignes")
    exemplaire = models.ForeignKey(Exemplaire, on_delete=models.CASCADE)
    statut_constate = models.CharField(max_length=20, choices=ETATS_EXEMPLAIRE)
    est_present = models.BooleanField(default=True)
    remarque = models.TextField(blank=True)

    class Meta:
        unique_together = ("inventaire", "exemplaire")
