"""
Module Paie - Modèles de données.

Contient :
  - PaiementSalaire        : enregistrement d'un paiement de salaire
  - ContratEmploye         : contrat d'embauche d'un membre du personnel
  - BulletinSalaire        : bulletin de salaire mensuel
  - RenouvellementContrat  : historique des renouvellements de contrat
"""

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal

from users.models import Personnel
from core.models import AnneeAcademique


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES
# ─────────────────────────────────────────────────────────────────────────────

JOURS_ALERTE_EXPIRATION = 30  # Nombre de jours avant expiration pour déclencher une alerte


# ─────────────────────────────────────────────────────────────────────────────
# PAIEMENT DE SALAIRE
# ─────────────────────────────────────────────────────────────────────────────

class PaiementSalaire(models.Model):
    reference = models.CharField(max_length=50, unique=True)

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="paiements_salaire",
    )

    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
    )

    mois = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    annee = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)]
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

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

    note = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_salary_payments",
    )

    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        related_name="confirmed_salary_payments",
        on_delete=models.PROTECT,
    )

    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Paiement de Salaire"
        verbose_name_plural = "Paiements de Salaire"
        indexes = [
            models.Index(fields=["personnel", "statut"]),
            models.Index(fields=["annee", "mois"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.reference} - {self.personnel}"


# ─────────────────────────────────────────────────────────────────────────────
# CONTRAT D'EMBAUCHE
# ─────────────────────────────────────────────────────────────────────────────

class ContratEmploye(models.Model):
    """
    Contrat d'embauche d'un membre du personnel.
    Définit le salaire de base, les règles de retenue en cas d'absence,
    les taux d'heures supplémentaires et les primes de motivation.
    """

    TYPE_CONTRAT = [
        ("CDI", "Contrat à Durée Indéterminée"),
        ("CDD", "Contrat à Durée Déterminée"),
        ("STAGE", "Stage"),
        ("INTERIM", "Intérim"),
        ("AUTRE", "Autre"),
    ]

    STATUT_CONTRAT = [
        ("ACTIF", "Actif"),
        ("EXPIRE", "Expiré"),
        ("RESILIE", "Résilié"),
        ("SUSPENDU", "Suspendu"),
        ("RENOUVELE", "Renouvelé"),
    ]

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="contrats",
    )

    type_contrat = models.CharField(
        max_length=20,
        choices=TYPE_CONTRAT,
        default="CDI",
    )

    poste = models.CharField(
        max_length=150,
        help_text="Intitulé du poste occupé (ex: Enseignant de Mathématiques)",
    )

    date_debut = models.DateField(
        help_text="Date de début du contrat",
    )

    date_fin = models.DateField(
        null=True,
        blank=True,
        help_text="Date de fin (laisser vide pour un CDI)",
    )

    salaire_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Salaire de base mensuel brut",
    )

    # ── Règles de retenue en cas d'absence ──────────────────────────────────
    nb_jours_ouvrable = models.PositiveSmallIntegerField(
        default=26,
        validators=[MinValueValidator(1), MaxValueValidator(31)],
        help_text="Nombre de jours ouvrables par mois (défaut: 26)",
    )

    taux_retenue_absence = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("100.00"),
        validators=[MinValueValidator(Decimal("0")), MaxValueValidator(Decimal("100"))],
        help_text="% du salaire journalier à retrancher par jour d'absence (100% = 1 journée complète)",
    )

    # ── Heures supplémentaires ───────────────────────────────────────────────
    taux_heure_supplementaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Montant fixe payé par heure supplémentaire",
    )

    # ── Prime de motivation ──────────────────────────────────────────────────
    prime_motivation = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Prime de motivation mensuelle fixe incluse dans le contrat",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CONTRAT,
        default="ACTIF",
    )

    observations = models.TextField(
        blank=True,
        null=True,
        help_text="Observations ou conditions particulières du contrat",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="contrats_crees",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["personnel", "statut"]),
            models.Index(fields=["date_debut", "date_fin"]),
        ]
        verbose_name = "Contrat Employé"
        verbose_name_plural = "Contrats Employés"

    def __str__(self):
        return f"[{self.type_contrat}] {self.personnel} — {self.poste} ({self.statut})"

    # ── Propriétés d'expiration ──────────────────────────────────────────────

    @property
    def days_until_expiry(self):
        """
        Retourne le nombre de jours restants avant l'expiration du contrat.
        Retourne None pour les CDI sans date_fin.
        Retourne un nombre négatif si le contrat est déjà expiré.
        """
        if self.date_fin is None:
            return None
        today = timezone.now().date()
        return (self.date_fin - today).days

    @property
    def is_expired(self):
        """
        Retourne True si la date de fin est dépassée ou si le statut est EXPIRE/RESILIE/RENOUVELE.
        """
        if self.statut in ("EXPIRE", "RESILIE", "RENOUVELE"):
            return True
        days = self.days_until_expiry
        if days is None:
            return False
        return days < 0

    @property
    def is_expiring_soon(self):
        """
        Retourne True si le contrat expire dans les JOURS_ALERTE_EXPIRATION prochains jours.
        Ne retourne pas True si le contrat est déjà expiré (is_expired == True).
        """
        days = self.days_until_expiry
        if days is None:
            return False
        return 0 <= days <= JOURS_ALERTE_EXPIRATION

    @property
    def statut_effectif(self):
        """
        Retourne le statut réel en tenant compte de la date du jour.
        Utile pour détecter les contrats expirés non encore mis à jour en base.
        """
        if self.statut == "ACTIF" and self.is_expired:
            return "EXPIRE"
        return self.statut

    # ── Propriétés de calcul ─────────────────────────────────────────────────

    @property
    def salaire_journalier(self):
        """Salaire journalier calculé sur la base des jours ouvrables du contrat."""
        if self.nb_jours_ouvrable > 0:
            return self.salaire_base / Decimal(str(self.nb_jours_ouvrable))
        return Decimal("0")

    def calculer_retenue_absence(self, nb_jours):
        """
        Calcule la retenue totale pour un nombre de jours d'absence.
        retenue = nb_jours × salaire_journalier × (taux_retenue_absence / 100)
        """
        nb_jours = Decimal(str(nb_jours))
        return nb_jours * self.salaire_journalier * (self.taux_retenue_absence / Decimal("100"))

    def calculer_montant_heures_sup(self, nb_heures):
        """Calcule le montant total pour un nombre d'heures supplémentaires."""
        return Decimal(str(nb_heures)) * self.taux_heure_supplementaire


# ─────────────────────────────────────────────────────────────────────────────
# BULLETIN DE SALAIRE
# ─────────────────────────────────────────────────────────────────────────────

class BulletinSalaire(models.Model):
    """
    Bulletin de salaire mensuel d'un membre du personnel.
    Calculé automatiquement à partir du contrat, des absences et des heures sup.

    Formule :
        salaire_net = salaire_base
                    - retenue_absence
                    + montant_heures_sup
                    + prime_motivation
                    + autres_primes
                    - autres_retenues
    """

    STATUT_BULLETIN = [
        ("BROUILLON", "Brouillon"),
        ("VALIDE", "Validé"),
        ("PAYE", "Payé"),
    ]

    contrat = models.ForeignKey(
        ContratEmploye,
        on_delete=models.PROTECT,
        related_name="bulletins",
        help_text="Contrat en vigueur au moment de la génération du bulletin",
    )

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="bulletins_salaire",
    )

    mois = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )

    annee = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )

    # ── Éléments du salaire ──────────────────────────────────────────────────
    salaire_base = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Salaire de base (copié depuis le contrat)",
    )

    # ── Retenues pour absences ───────────────────────────────────────────────
    nb_jours_absence = models.PositiveSmallIntegerField(
        default=0,
        help_text="Nombre de jours d'absence non justifiés",
    )

    retenue_absence = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Montant retranché au titre des absences (calculé automatiquement)",
    )

    # ── Heures supplémentaires ───────────────────────────────────────────────
    nb_heures_supplementaires = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Nombre d'heures supplémentaires effectuées",
    )

    montant_heures_sup = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Montant ajouté pour les heures supplémentaires (calculé automatiquement)",
    )

    # ── Primes ───────────────────────────────────────────────────────────────
    prime_motivation = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Prime de motivation ce mois-ci (peut différer du contrat)",
    )

    autres_primes = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Autres primes exceptionnelles (bonus, ancienneté, etc.)",
    )

    note_primes = models.TextField(
        blank=True,
        null=True,
        help_text="Description des primes supplémentaires",
    )

    # ── Retenues supplémentaires ─────────────────────────────────────────────
    autres_retenues = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Autres retenues (avances, pénalités, etc.)",
    )

    note_retenues = models.TextField(
        blank=True,
        null=True,
        help_text="Description des retenues supplémentaires",
    )

    # ── Résultat ─────────────────────────────────────────────────────────────
    salaire_net = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0"),
        help_text="Salaire net à payer (calculé automatiquement)",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_BULLETIN,
        default="BROUILLON",
    )

    paiement = models.OneToOneField(
        PaiementSalaire,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulletin",
        help_text="Paiement associé lorsque le bulletin est payé",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="bulletins_crees",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("personnel", "mois", "annee")
        ordering = ["-annee", "-mois"]
        indexes = [
            models.Index(fields=["personnel", "statut"]),
            models.Index(fields=["annee", "mois"]),
            models.Index(fields=["created_at"]),
        ]
        verbose_name = "Bulletin de Salaire"
        verbose_name_plural = "Bulletins de Salaire"

    def __str__(self):
        return f"Bulletin {self.mois:02d}/{self.annee} — {self.personnel}"

    # ── Calculs ──────────────────────────────────────────────────────────────

    def recalculer(self):
        """
        Recalcule les montants à partir du contrat et des données saisies.
        Appelé avant la sauvegarde ou manuellement.
        """
        self.retenue_absence = self.contrat.calculer_retenue_absence(self.nb_jours_absence)
        self.montant_heures_sup = self.contrat.calculer_montant_heures_sup(
            self.nb_heures_supplementaires
        )
        total_gains = (
            self.salaire_base
            + self.montant_heures_sup
            + self.prime_motivation
            + self.autres_primes
        )
        total_retenues = self.retenue_absence + self.autres_retenues
        self.salaire_net = max(total_gains - total_retenues, Decimal("0"))

    def save(self, *args, **kwargs):
        """Recalcule automatiquement le salaire net avant la sauvegarde."""
        self.recalculer()
        super().save(*args, **kwargs)

    @property
    def total_gains(self):
        return self.salaire_base + self.montant_heures_sup + self.prime_motivation + self.autres_primes

    @property
    def total_retenues(self):
        return self.retenue_absence + self.autres_retenues


# ─────────────────────────────────────────────────────────────────────────────
# RENOUVELLEMENT DE CONTRAT
# ─────────────────────────────────────────────────────────────────────────────

class RenouvellementContrat(models.Model):
    """
    Historique des renouvellements de contrat.
    Chaque renouvellement lie l'ancien contrat (RENOUVELE) au nouveau contrat (ACTIF).

    Workflow :
        1. DRH appelle POST /paie/contrats/{id}/renouveler/ avec les nouvelles conditions
        2. L'ancien contrat passe au statut RENOUVELE
        3. Un nouveau contrat ACTIF est créé avec les nouvelles conditions
        4. Un enregistrement RenouvellementContrat est créé pour tracer l'historique
    """

    ancien_contrat = models.OneToOneField(
        ContratEmploye,
        on_delete=models.PROTECT,
        related_name="renouvellement",
        help_text="Contrat initial qui a été renouvelé",
    )

    nouveau_contrat = models.OneToOneField(
        ContratEmploye,
        on_delete=models.PROTECT,
        related_name="issu_de_renouvellement",
        help_text="Nouveau contrat issu du renouvellement",
    )

    date_renouvellement = models.DateField(
        help_text="Date effective du renouvellement",
    )

    motif = models.TextField(
        blank=True,
        null=True,
        help_text="Motif ou raison du renouvellement",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="renouvellements_contrat",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Renouvellement de Contrat"
        verbose_name_plural = "Renouvellements de Contrats"

    def __str__(self):
        return (
            f"Renouvellement [{self.date_renouvellement}] "
            f"{self.ancien_contrat.personnel} : "
            f"Contrat #{self.ancien_contrat_id} → #{self.nouveau_contrat_id}"
        )
