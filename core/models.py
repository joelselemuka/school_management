from django.db import models
from datetime import date
from django.core.exceptions import ValidationError
from common.models import ActiveManager, SoftDeleteModel
from common.utils import get_jour_map
from dateutil.relativedelta import relativedelta


class Ecole(models.Model):
    """Configuration de l'école."""
    
    WEEK_TYPE_CHOICES = [
        ("ANGLAISE", "Semaine anglaise (Lundi - Vendredi)"),
        ("NORMALE", "Semaine normale (Lundi - Samedi)"),
    ]

    nom = models.CharField(max_length=255)
    adresse = models.CharField(max_length=255)
    telephone = models.CharField(max_length=50)
    email = models.EmailField(max_length=255, blank=True, null=True)
    site_web = models.URLField(max_length=255, blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    devise = models.CharField(max_length=255, blank=True, null=True, help_text="Slogan de l'école")
    description = models.TextField(blank=True, null=True)
    
    week_type = models.CharField(
        max_length=20,
        choices=WEEK_TYPE_CHOICES,
        default="NORMALE"
    )
    allow_discount = models.BooleanField(default=False)

    teacher_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    siblings_discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    siblings_min_count = models.IntegerField(default=2)

    # ── Paramètres RH (paie du personnel) ───────────────────────────────────────────
    taux_retenue_absence_defaut = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=100,
        help_text=(
            "Taux de retenue (%) apppliqué par jour d'absence non justifié. "
            "100 = 1 journée complète. Utilisé comme valeur par défaut "
            "lors de la création d'un nouveau contrat."
        )
    )

    taux_heure_supplementaire_defaut = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=(
            "Montant fixé payé par heure supplémentaire (en devise locale). "
            "Utilisé comme valeur par défaut lors de la création d'un nouveau contrat."
        )
    )

    # ── Paramètres de timing des cours ────────────────────────────────────────
    heure_debut_cours = models.TimeField(
        default='07:30',
        help_text="Heure de début de la 1ère heure d'étude (ex: 07:30)"
    )
    duree_heure_etude = models.PositiveIntegerField(
        default=50,
        help_text="Durée d'une heure d'étude en minutes (ex: 50)"
    )
    heure_recreation_apres = models.PositiveIntegerField(
        default=3,
        help_text="La récréation vient après quelle heure d'étude (ex: 3 = après la 3e heure)"
    )
    duree_recreation = models.PositiveIntegerField(
        default=30,
        help_text="Durée de la récréation en minutes (ex: 30)"
    )
    
    # ── Paramètres Bibliothèque (Pénalités Retards) ───────────────────────────
    biblio_jours_avant_penalite = models.PositiveIntegerField(
        default=0,
        help_text="Nombre de jours de tolérance après la date limite avant d'appliquer la pénalité (0 = immédiat)"
    )
    biblio_montant_penalite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Montant de la pénalité"
    )
    biblio_type_penalite = models.CharField(
        max_length=20,
        choices=[("FIXE", "Montant Fixe"), ("PAR_JOUR", "Taux par jour de retard")],
        default="FIXE"
    )
    # ──────────────────────────────────────────────────────────────────────────

    actif = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_ecole'
        verbose_name = 'École'
        verbose_name_plural = 'Écoles'
    
    def __str__(self):
        return self.nom

    @classmethod
    def get_configuration(cls):
        """
        Retourne la configuration active de l'école.
        Lève une ValidationError si aucune école n'est configurée.
        Cette méthode est utilisée comme prérequis obligatoire avant toute
        création de personnel ou de contrat.
        """
        ecole = cls.objects.filter(actif=True).first()
        if ecole is None:
            raise ValidationError(
                "Aucune configuration d'école active trouvée. "
                "Veuillez d'abord configurer l'école (Core > École) avant de "
                "créer du personnel ou des contrats."
            )
        return ecole


# Alias pour compatibilité avec l'ancien code
SchoolConfiguration = Ecole



class AnneeAcademique(SoftDeleteModel):
    nom = models.CharField(max_length=32, unique=True)
    date_debut = models.DateField()
    date_fin = models.DateField()
    date_debut_inscriptions = models.DateField(null=True, blank=True)
    date_fin_inscriptions = models.DateField(null=True, blank=True)

    class Meta:
        db_table = 'core_anneeacademique'
        verbose_name = 'Année Académique'
        verbose_name_plural = 'Années Académiques'
        indexes = [
            models.Index(fields=["actif"]),
            models.Index(fields=["date_debut", "date_fin"]),
        ]
    
    objects = ActiveManager()

    def clean(self):
        # 1. durée minimum 8 mois
        if self.date_fin <= self.date_debut:
            raise ValidationError("date_fin doit être supérieure à date_debut")

        if self.date_fin < self.date_debut + relativedelta(months=8):
            raise ValidationError(
                "Une année académique doit durer au moins 8 mois"
            )

        # 2. début inscription
        min_debut = self.date_debut - relativedelta(months=2)
        max_debut = self.date_debut + relativedelta(months=2)

        if not (min_debut <= self.date_debut_inscriptions <= max_debut):
            raise ValidationError(
                "date debut inscriptions doit être entre "
                "2 mois avant et 2 mois après date_debut"
            )

        # 3. fin inscription logique
        if self.date_fin_inscriptions <= self.date_debut_inscriptions:
            raise ValidationError(
                "fin_inscription doit être supérieure à date_debut_inscriptions"
            )

        if self.date_fin_inscriptions > self.date_fin:
            raise ValidationError(
                "date fin inscription ne peut dépasser la fin de l'année"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        if self.actif:
            AnneeAcademique.objects.filter(
                actif=True
            ).update(actif=False)

        super().save(*args, **kwargs)
    
    @classmethod
    def get_active(cls):
        return cls.objects.filter(actif=True).first()
    
    @property
    def est_active(self):
        """Vérifie si l'année est actuellement active."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.actif and self.date_debut <= today <= self.date_fin

    def __str__(self):
        return self.nom


TRIMESTRE_CHOICES = [
    ("trimestre_1", "1er Trimestre"),
    ("trimestre_2", "2e Trimestre"),
    ("trimestre_3", "3e Trimestre"),
]


class Periode(SoftDeleteModel):
    nom = models.CharField(max_length=50)
    trimestre = models.CharField(max_length=20, choices=TRIMESTRE_CHOICES, default="trimestre_1")
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE, related_name="periodes")
    date_debut = models.DateField()
    date_fin = models.DateField()

    class Meta:
        db_table = 'core_periode'
        verbose_name = 'Période'
        verbose_name_plural = 'Périodes'
        unique_together = ("nom", "annee_academique")
        indexes = [
            models.Index(fields=["annee_academique"]),
            models.Index(fields=["date_debut", "date_fin"]),
            models.Index(fields=["actif"]),
        ]
    
    objects = ActiveManager()

    def clean(self):
        annee = self.annee_academique

        # 1. intervalle dans l'année
        if not (annee.date_debut <= self.date_debut <= annee.date_fin):
            raise ValidationError(
                "date_debut hors intervalle année académique"
            )

        if not (annee.date_debut <= self.date_fin <= annee.date_fin):
            raise ValidationError(
                "date_fin hors intervalle année académique"
            )

        # 2. durée max 4 mois
        if self.date_fin > self.date_debut + relativedelta(months=4):
            raise ValidationError(
                "Une période ne peut dépasser 4 mois"
            )

        # 3. max 3 périodes même trimestre
        count = Periode.objects.filter(
            annee_academique=annee,
            trimestre=self.trimestre
        ).exclude(pk=self.pk).count()

        if count >= 3:
            raise ValidationError(
                "Maximum 3 périodes pour un même trimestre"
            )

        # 4. continuité obligatoire
        last = (
            Periode.objects
            .filter(annee_academique=annee)
            .exclude(pk=self.pk)
            .order_by("-date_fin")
            .first()
        )

        if last:
            if self.date_debut != last.date_fin:
                raise ValidationError(
                    f"La période doit commencer à "
                    f"{last.date_fin}"
                )

        # 5. cohérence logique
        if self.date_fin <= self.date_debut:
            raise ValidationError(
                "date_fin doit être > date_debut"
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def soft_delete(self):
        """Marquer cette période comme inactive (soft delete)."""
        self.actif = False
        self.save()

    def restore(self):
        """Restaurer cette période (passer actif=True)."""
        if not self.actif:
            self.actif = True
            self.save()

    @classmethod
    def get_actifs(cls):
        """Retourne un queryset des périodes actives."""
        return cls.objects.filter(actif=True)

    @classmethod
    def get_inactifs(cls):
        """Retourne un queryset des périodes inactives."""
        return cls.objects.filter(actif=False)

    @classmethod
    def restore_all(cls):
        """Restaurer toutes les périodes inactives (retourne le nombre modifié)."""
        qs = cls.objects.filter(actif=False)
        return qs.update(actif=True)

    @classmethod
    def deactivate_all(cls):
        """Désactiver toutes les périodes actives (retourne le nombre modifié)."""
        qs = cls.objects.filter(actif=True)
        return qs.update(actif=False)
    
    def contains(self, d):
        return self.date_debut <= d <= self.date_fin

    @classmethod
    def of_date(cls, annee_academique, d):
        return cls.objects.filter(
            annee_academique=annee_academique,
            date_debut__lte=d, 
            date_fin__gte=d,
            actif=True
        ).first()
    
    @property
    def est_active(self):
        """Vérifie si la période est actuellement active."""
        from django.utils import timezone
        today = timezone.now().date()
        return self.actif and self.date_debut <= today <= self.date_fin

    def __str__(self):
        return f"{self.nom} - {self.annee_academique.nom}"


days = (
    ("LUN", "Lundi"),
    ("MAR", "Mardi"),
    ("MER", "Mercredi"),
    ("JEU", "Jeudi"),
    ("VEN", "Vendredi"),
    ("SAM", "Samedi"),
)


class HollyDays(models.Model):
    jour = models.CharField(max_length=20, choices=days)
    date = models.DateField()
    description = models.CharField(max_length=255)
    
    class Meta:
        db_table = 'core_hollydays'
        verbose_name = 'Jour Férié'
        verbose_name_plural = 'Jours Fériés'
    
    def __str__(self):
        return f"{self.jour} {self.date} ({self.description})"


class ReglePromotion(models.Model):
    """Règles de promotion automatique des élèves."""
    
    nom = models.CharField(max_length=200)
    classe_origine = models.ForeignKey(
        'academics.Classe',
        on_delete=models.CASCADE,
        related_name='regles_promotion_origine'
    )
    classe_destination = models.ForeignKey(
        'academics.Classe',
        on_delete=models.CASCADE,
        related_name='regles_promotion_destination'
    )
    moyenne_minimale = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Moyenne minimale requise pour la promotion"
    )
    taux_presence_minimal = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=75,
        help_text="Taux de présence minimal en pourcentage"
    )
    est_active = models.BooleanField(default=True)
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.CASCADE,
        related_name='regles_promotion'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'core_reglepromotion'
        verbose_name = 'Règle de Promotion'
        verbose_name_plural = 'Règles de Promotion'
        unique_together = ('classe_origine', 'annee_academique')
        indexes = [
            models.Index(fields=['classe_origine']),
            models.Index(fields=['annee_academique']),
            models.Index(fields=['est_active']),
        ]
    
    @property
    def actif(self):
        """Alias pour est_active pour compatibilité."""
        return self.est_active
    
    def __str__(self):
        return f"{self.classe_origine} → {self.classe_destination}"
