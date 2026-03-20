from datetime import timedelta, datetime, time as time_type

from django.db import models
from django.db.models import Count, Q
from academics.models import Classe, Cours
from core.models import AnneeAcademique, Periode
from users.models import Eleve, Personnel
from common.models import SoftDeleteModel
from django.core.exceptions import ValidationError

JOUR_CHOICES = [
    ("LUNDI", "Lundi"),
    ("MARDI", "Mardi"),
    ("MERCREDI", "Mercredi"),
    ("JEUDI", "Jeudi"),
    ("VENDREDI", "Vendredi"),
    ("SAMEDI", "Samedi"),
]



class HoraireCours(SoftDeleteModel):
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE, related_name='horaires')
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name='horaires')
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)
    salle = models.CharField(max_length=50, blank=True)
    jour = models.CharField(max_length=10, choices=JOUR_CHOICES)
    # Numéro de l'heure dans la journée (1 = 1ère heure, 2 = 2e heure, etc.)
    # heure_debut et heure_fin sont calculés automatiquement à partir de ce numéro + config école
    numero_heure = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Numéro de l'heure dans la journée (1=1ère heure, 2=2e heure, ...)"
    )
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()

    class Meta:
        ordering = ['jour', 'numero_heure', 'heure_debut']
        indexes = [
            models.Index(fields=['classe', 'jour']),
            models.Index(fields=['cours']),
            models.Index(fields=['annee_academique']),
        ]

    def clean(self):
        from common.utils import get_jour_map

        jour_map = get_jour_map()

        if self.jour not in jour_map:
            raise ValidationError("Jour non ouvrable selon la configuration de l'école")

        # Vérifier qu'il n'y a pas de conflit d'horaire (même classe, même jour, même heure)
        if self.numero_heure:
            conflict = HoraireCours.objects.filter(
                classe=self.classe,
                annee_academique=self.annee_academique,
                jour=self.jour,
                numero_heure=self.numero_heure,
                actif=True
            ).exclude(pk=self.pk).exists()
            if conflict:
                raise ValidationError(
                    f"Conflit d'horaire : la {self.numero_heure}e heure du {self.jour} "
                    f"est déjà occupée pour cette classe."
                )

    def __str__(self):
        return f"{self.cours.nom} – {self.jour} H{self.numero_heure or ''} ({self.heure_debut}-{self.heure_fin})"


class ClasseHoraireConfig(models.Model):
    """
    Configuration du nombre d'heures par jour pour chaque classe.
    Permet à certaines classes d'avoir plus de 6 heures sur certains jours.
    """
    classe = models.OneToOneField(
        Classe, on_delete=models.CASCADE, related_name='horaire_config'
    )
    annee_academique = models.ForeignKey(
        AnneeAcademique, on_delete=models.PROTECT, related_name='horaire_configs'
    )
    heures_max_par_jour = models.PositiveIntegerField(
        default=6,
        help_text="Nombre maximum d'heures d'étude par jour pour cette classe (ex: 6 ou 8)"
    )
    # Jours qui peuvent avoir plus de 6 heures (si heures_max_par_jour > 6)
    jours_prolonges = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            'Jours avec des heures supplémentaires (au-delà de 6), ex: ["LUNDI","MERCREDI"]. '
            'Ignorer si heures_max_par_jour <= 6.'
        )
    )

    class Meta:
        db_table = 'attendance_classehoraireconfig'
        verbose_name = 'Config Horaire Classe'
        verbose_name_plural = 'Configs Horaire Classes'

    def clean(self):
        if self.heures_max_par_jour < 1 or self.heures_max_par_jour > 12:
            raise ValidationError("heures_max_par_jour doit être entre 1 et 12.")
        # Valider les jours prolongés
        jours_valides = {c[0] for c in JOUR_CHOICES}
        for j in (self.jours_prolonges or []):
            if j not in jours_valides:
                raise ValidationError(f"Jour invalide dans jours_prolonges : {j}")

    def __str__(self):
        return f"Config {self.classe.nom} – {self.heures_max_par_jour}h/jour"


class HoraireEnseignant(models.Model):
    """
    Horaire d'un enseignant, dérivé automatiquement depuis HoraireCours
    et AffectationEnseignant. Généralement généré par TeacherScheduleService.
    """
    enseignant = models.ForeignKey(
        Personnel, on_delete=models.CASCADE, related_name='horaires_enseignant'
    )
    horaire_cours = models.ForeignKey(
        HoraireCours, on_delete=models.CASCADE, related_name='horaires_enseignants'
    )
    annee_academique = models.ForeignKey(
        AnneeAcademique, on_delete=models.PROTECT, related_name='horaires_enseignants'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'attendance_horaireenseignant'
        verbose_name = 'Horaire Enseignant'
        verbose_name_plural = 'Horaires Enseignants'
        unique_together = ('enseignant', 'horaire_cours')
        ordering = ['horaire_cours__jour', 'horaire_cours__numero_heure']
        indexes = [
            models.Index(fields=['enseignant', 'annee_academique']),
            models.Index(fields=['horaire_cours']),
        ]

    def __str__(self):
        hc = self.horaire_cours
        return (
            f"{self.enseignant} – {hc.cours.nom} "
            f"({hc.jour} H{hc.numero_heure})"
        )




PRESENCE_STATUS = [
    ("present", "Présent"),
    ("absent", "Absent"),
    ("retard", "Retard"),
    ("malade", "Malade"),
    ("en_deuil", "En deuil"),
]

class SeanceCours(SoftDeleteModel):
    horaire = models.ForeignKey(HoraireCours, on_delete=models.PROTECT)
    cours = models.ForeignKey(Cours, on_delete=models.PROTECT)
    classe = models.ForeignKey(Classe, on_delete=models.PROTECT)
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)

    date = models.DateField()
    is_locked = models.BooleanField(default=False)
    is_holiday = models.BooleanField(default=False)
    type = models.CharField(
        max_length=20,
        choices=[("cours", "Cours"), ("examen", "Examen")],
        default="cours"
    )

    is_suspended = models.BooleanField(default=False)


class Presence(SoftDeleteModel):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="presences")
    seance = models.ForeignKey(
        SeanceCours, on_delete=models.CASCADE, related_name="presences"
    )
    statut = models.CharField(max_length=10, choices=PRESENCE_STATUS, default="present")
    remarque = models.TextField(blank=True)
   

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["eleve","seance"],
                condition=Q(actif=True),
                name="eleve_seance_unique_presence"
            )
        ]
        ordering = ["seance__horaire__jour", "seance__horaire__heure_debut"]
        indexes = [
                models.Index(fields=["eleve"]),
                models.Index(fields=["seance"]),
                models.Index(fields=["statut"]),
            ]
    def __str__(self):
        return f"{self.eleve} - {self.seance} - {self.get_statut_display()}"

class JustificationAbsence(SoftDeleteModel):
    presence = models.OneToOneField(Presence,on_delete=models.CASCADE)
    motif = models.TextField()
    document = models.FileField(upload_to="justifs/",blank=True,null=True)
    valide = models.BooleanField(default=False)

class DisciplineRecord(SoftDeleteModel):
    eleve=models.ForeignKey(Eleve,on_delete=models.CASCADE)
    niveau=models.CharField(max_length=30)
    date=models.DateField(auto_now_add=True)


class DisciplineRule(models.Model):
    seuil = models.PositiveIntegerField()
    niveau = models.CharField(max_length=30)  # avertissement / convocation / exclusion
    actif = models.BooleanField(default=True)

    class Meta:
        ordering = ["seuil"]

    def __str__(self):
        return f"{self.seuil} → {self.niveau}"

class Holiday(models.Model):
    date = models.DateField(unique=True)
    label = models.CharField(max_length=100, blank=True)
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.CASCADE,
        related_name="holidays"
    )

    class Meta:
        ordering = ["date"]

    def __str__(self):
        return f"{self.date} - {self.label}"

CALENDAR_EVENT_TYPE = [
    ("holiday", "Jour férié"),
    ("vacation", "Vacances scolaires"),
    ("exam", "Examen"),
    ("exception", "Exception ponctuelle"),
]

class AcademicCalendarEvent(models.Model):
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.CASCADE,
        related_name="calendar_events"
    )

    type = models.CharField(max_length=20, choices=CALENDAR_EVENT_TYPE)
    label = models.CharField(max_length=100)

    date_debut = models.DateField()
    date_fin = models.DateField()

    classes = models.ManyToManyField(
        Classe,
        blank=True,
        help_text="Vide = toutes les classes"
    )

    suspend_cours = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date_debut"]

    def applies_to(self, date, classe):
        if not (self.date_debut <= date <= self.date_fin):
            return False
        if self.classes.exists() and classe not in self.classes.all():
            return False
        return True


class AttendanceSummary(models.Model):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE)
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE)

    absences = models.PositiveIntegerField(default=0)
    retards = models.PositiveIntegerField(default=0)

    is_blocking = models.BooleanField(default=False)

    class Meta:
        unique_together = ("eleve", "periode")


# ============================================================================
# PRÉSENCE DU PERSONNEL
# ============================================================================

PRESENCE_PERSONNEL_STATUS = [
    ("present", "Présent"),
    ("absent", "Absent"),
    ("retard", "Retard"),
    ("remplace", "Remplacé"),
    ("conge", "Congé"),
]


class PresencePersonnel(SoftDeleteModel):
    """
    Enregistre la présence d'un membre du personnel pour une journée donnée.
    Couvre tous les rôles : enseignant, comptable, secrétaire, DRH, etc.
    Alimenté manuellement ou par pointage, ce modèle est la source de vérité
    pour le calcul des absences dans les bulletins de salaire.
    """

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        related_name="presences_travail",
    )
    date = models.DateField(help_text="Journée concernée")
    statut = models.CharField(
        max_length=16,
        choices=PRESENCE_PERSONNEL_STATUS,
        default="present",
    )
    remplacant = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="remplacements",
        help_text="Personnel remplaçant (si statut=remplace)",
    )
    conge_justifie = models.BooleanField(
        default=False,
        help_text="Absence justifiée (congé maladie, congé payé, etc.) — non déduit de la paie",
    )
    remarque = models.TextField(blank=True, null=True)
    enregistre_par = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="presences_personnel_enregistrees",
    )

    class Meta:
        unique_together = ("personnel", "date")
        indexes = [
            models.Index(fields=["personnel", "date"]),
            models.Index(fields=["statut"]),
            models.Index(fields=["date"]),
        ]
        ordering = ["-date"]
        verbose_name = "Présence Personnel"
        verbose_name_plural = "Présences Personnel"

    def __str__(self):
        return f"{self.personnel} — {self.date} : {self.get_statut_display()}"

    @property
    def est_absent_non_justifie(self):
        """True si l'absence doit être déduite de la paie."""
        return self.statut == "absent" and not self.conge_justifie


class SommairePaiePersonnel(models.Model):
    """
    Résumé mensuel des présences d'un personnel pour un mois/année donné.
    Calculé à partir de PresencePersonnel et utilisé directement pour
    pré-remplir les bulletins de salaire (nb_jours_absence).
    """
    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        related_name="sommaires_paie",
    )
    mois = models.PositiveSmallIntegerField()
    annee = models.PositiveSmallIntegerField()
    nb_jours_travailles = models.PositiveSmallIntegerField(default=0)
    nb_jours_absence = models.PositiveSmallIntegerField(
        default=0,
        help_text="Absences non justifiées (déductibles de la paie)",
    )
    nb_jours_conge = models.PositiveSmallIntegerField(
        default=0,
        help_text="Congés justifiés (non déduits)",
    )
    nb_jours_retard = models.PositiveSmallIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("personnel", "mois", "annee")
        indexes = [
            models.Index(fields=["personnel", "annee", "mois"]),
        ]
        ordering = ["-annee", "-mois"]
        verbose_name = "Sommaire Paie Personnel"
        verbose_name_plural = "Sommaires Paie Personnel"

    def __str__(self):
        return f"{self.personnel} — {self.mois:02d}/{self.annee}"

