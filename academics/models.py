
from decimal import Decimal

from django.db import models
from datetime import date
from django.core.exceptions import ValidationError

from common.models import ActiveManager, SoftDeleteModel
from core.models import AnneeAcademique, Periode
from users.models import Eleve, Personnel, User



CLASSES_NIVEAU = [
    ("creche", "Crèche"),
    ("primaire", "Primaire"),
    ("secondaire", "Secondaire"),
    ("humanite", "Humanité"),
]



class Classe(SoftDeleteModel):
    nom = models.CharField(max_length=50)
    niveau = models.CharField(max_length=50, choices=CLASSES_NIVEAU, default="primaire")
    annee_academique = models.ForeignKey(
        AnneeAcademique, on_delete=models.PROTECT, related_name="classes"
    )
    responsable = models.ForeignKey(
        Personnel, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="titulaire"
    )

    class Meta:
        unique_together = ("nom", "annee_academique")
        indexes = [
            models.Index(fields=["annee_academique"]),
            models.Index(fields=["niveau"]),
            models.Index(fields=["actif"]),
        ]

    @property
    def effectif(self):
        return self.inscriptions.filter(actif=True).count()

    def __str__(self):
        return f"{self.nom} - {self.annee_academique.nom}"




class Cours(SoftDeleteModel):
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=20)
    classe = models.ForeignKey(Classe, on_delete=models.CASCADE, related_name="cours")
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("1.00"))
    volume_horaire = models.PositiveIntegerField(
        default=1,
        help_text="Volume horaire hebdomadaire (poids relatif pour la génération d'horaire). Ex: 4 = 4h/semaine"
    )
    annee_academique = models.ForeignKey(
        AnneeAcademique,
        on_delete=models.PROTECT,
        related_name="cours"
    )

    class Meta:
        # Un code de cours est unique par classe (pas globalement)
        unique_together = ("code", "classe")
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["classe"]),
            models.Index(fields=["annee_academique"]),
            models.Index(fields=["actif"]),
        ]

    def clean(self):
        if self.annee_academique_id != self.classe.annee_academique_id:
            raise ValidationError("Cours et Classe doivent appartenir à la même année académique.")
        if self.coefficient <= 0:
            raise ValidationError("Le coefficient doit être strictement positif.")

    def __str__(self):
        return f"{self.nom} ({self.classe.nom})"

class AffectationEnseignant(SoftDeleteModel):
    teacher = models.ForeignKey(Personnel, on_delete=models.CASCADE,related_name="affectations",)
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE,related_name="affectations",)
    role = models.CharField(max_length=50, choices=[('titulaire','Titulaire'),('remplacant','Remplaçant')])
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('teacher', 'cours', 'start_date')




class Bulletin(SoftDeleteModel):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="bulletins")
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.CASCADE)
    periode = models.ForeignKey(Periode, on_delete=models.CASCADE)

    moyenne_generale = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    rang = models.PositiveIntegerField(null=True, blank=True)
    mention = models.CharField(max_length=64, blank=True)
    classe = models.ForeignKey(
        Classe,
        on_delete=models.PROTECT
    )
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("eleve", "periode", "annee_academique")
        indexes = [
            models.Index(fields=["eleve", "annee_academique"]),
            models.Index(fields=["periode"]),
        ]

    def clean(self):
        if self.periode.annee_academique_id != self.annee_academique_id:
            raise ValidationError("Incohérence année académique / période.")
        

    def __str__(self):
        return f"Bulletin {self.periode.nom} - {self.eleve}"





class Evaluation(SoftDeleteModel):
    TYPE_CHOICES = [
        ("interro", "Interrogation"),
        ("devoir", "Devoir"),
        ("examen", "Examen"),
        ("autre", "Autre"),
    ]
    cours = models.ForeignKey(Cours, on_delete=models.CASCADE)
    periode = models.ForeignKey(Periode, on_delete=models.PROTECT)
    annee_academique = models.ForeignKey(AnneeAcademique, on_delete=models.PROTECT)
    type_evaluation = models.CharField(max_length=32, choices=TYPE_CHOICES, default="autre")
    nom = models.CharField(max_length=100)
    bareme = models.IntegerField(default=20)
    poids = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1
    )
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    
    class Meta:
        indexes = [
            models.Index(fields=["cours"]),
            models.Index(fields=["periode"]),
            
        ]
    def clean(self):
        
        if self.bareme <= 0:
            raise ValidationError("Le barème doit être strictement positif.")
        if self.poids <= 0:
            raise ValidationError("Le poids doit être strictement positif.")
        if self.periode and self.periode.annee_academique_id != self.cours.classe.annee_academique_id:
            raise ValidationError("La période doit appartenir à la même année académique que le cours.")

    def __str__(self):
        return f"{self.nom} - {self.cours}"




class Note(SoftDeleteModel):
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name="notes")
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name="notes")
    valeur = models.DecimalField(max_digits=5, decimal_places=2)
    date_saisie = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)


    class Meta:
        unique_together = ("eleve", "evaluation")
        indexes = [
            models.Index(fields=["eleve"]),
            models.Index(fields=["evaluation"]),
        ]

    def clean(self):
        from admission.models import Inscription
        if self.valeur < 0:
            raise ValidationError("La valeur de la note ne peut être négative.")
        
        inscription = Inscription.objects.filter(
            eleve=self.eleve,
            classe=self.evaluation.cours.classe,
            annee_academique=self.evaluation.annee_academique,
            actif=True
        ).exists()

        if not inscription:
            raise ValidationError("cet eleve n'appartient pas à ce cours!")

        # Optionnel: valider que l'élève est inscrit dans la classe du cours pour l'année/période
        # via admissions.Inscription (requiert import tardif pour éviter cycles).

    def __str__(self):
        return f"{self.eleve} - {self.evaluation}: {self.valeur}/{self.evaluation.bareme}"


# ============================================================================
# GESTION DES EXAMENS ET SALLES
# ============================================================================

class Salle(SoftDeleteModel):
    """Salle de classe ou d'examen."""
    
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Code unique de la salle (ex: A101, B205)"
    )
    nom = models.CharField(max_length=100)
    batiment = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Nom du bâtiment"
    )
    capacite = models.IntegerField(
        help_text="Capacité maximale en nombre de places"
    )
    type_salle = models.CharField(
        max_length=50,
        choices=[
            ('classe', 'Classe'),
            ('examen', 'Salle d\'examen'),
            ('labo', 'Laboratoire'),
            ('amphi', 'Amphithéâtre'),
        ],
        default='classe'
    )
    equipements = models.TextField(
        blank=True,
        null=True,
        help_text="Liste des équipements disponibles"
    )
    est_disponible = models.BooleanField(
        default=True,
        help_text="Salle disponible pour utilisation"
    )
    
    class Meta:
        db_table = 'academics_salle'
        verbose_name = 'Salle'
        verbose_name_plural = 'Salles'
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['type_salle']),
            models.Index(fields=['est_disponible']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.nom}"
    
    @property
    def places_disponibles(self):
        """Retourne le nombre de places disponibles."""
        return self.capacite


class SessionExamen(SoftDeleteModel):
    """Session d'examen (ex: Examens du 1er trimestre)."""
    
    nom = models.CharField(
        max_length=200,
        help_text="Nom de la session (ex: Examens 1er Trimestre 2026)"
    )
    periode = models.ForeignKey(
        Periode,
        on_delete=models.CASCADE,
        related_name='sessions_examen'
    )
    date_debut = models.DateField()
    date_fin = models.DateField()
    type_session = models.CharField(
        max_length=50,
        choices=[
            ('interrogation', 'Interrogations'),
            ('examen_partiel', 'Examen Partiel'),
            ('examen_final', 'Examen Final'),
        ],
        default='examen_final'
    )
    instructions = models.TextField(
        blank=True,
        null=True,
        help_text="Instructions générales pour cette session"
    )
    statut = models.CharField(
        max_length=20,
        choices=[
            ('planifie', 'Planifié'),
            ('en_cours', 'En cours'),
            ('termine', 'Terminé'),
        ],
        default='planifie',
        db_index=True
    )
    
    class Meta:
        db_table = 'academics_sessionexamen'
        verbose_name = 'Session d\'Examen'
        verbose_name_plural = 'Sessions d\'Examens'
        ordering = ['-date_debut']
        indexes = [
            models.Index(fields=['periode']),
            models.Index(fields=['date_debut', 'date_fin']),
            models.Index(fields=['statut']),
        ]
    
    def clean(self):
        if self.date_fin <= self.date_debut:
            raise ValidationError("La date de fin doit être après la date de début")
    
    def __str__(self):
        return f"{self.nom} ({self.periode})"


class PlanificationExamen(SoftDeleteModel):
    """Planification d'un examen dans une salle."""
    
    evaluation = models.ForeignKey(
        Evaluation,
        on_delete=models.CASCADE,
        related_name='planifications'
    )
    session_examen = models.ForeignKey(
        SessionExamen,
        on_delete=models.CASCADE,
        related_name='planifications',
        null=True,
        blank=True
    )
    salle = models.ForeignKey(
        Salle,
        on_delete=models.CASCADE,
        related_name='planifications_examen'
    )
    date_examen = models.DateField()
    heure_debut = models.TimeField()
    heure_fin = models.TimeField()
    duree_minutes = models.IntegerField(
        help_text="Durée de l'examen en minutes"
    )
    surveillants = models.ManyToManyField(
        Personnel,
        related_name='surveillances',
        blank=True,
        limit_choices_to={'fonction': 'enseignant'}
    )
    instructions_surveillants = models.TextField(
        blank=True,
        null=True,
        help_text="Instructions pour les surveillants"
    )
    
    class Meta:
        db_table = 'academics_planificationexamen'
        verbose_name = 'Planification d\'Examen'
        verbose_name_plural = 'Planifications d\'Examens'
        ordering = ['date_examen', 'heure_debut']
        indexes = [
            models.Index(fields=['evaluation']),
            models.Index(fields=['salle']),
            models.Index(fields=['date_examen']),
            models.Index(fields=['session_examen']),
        ]
        unique_together = [
            ('salle', 'date_examen', 'heure_debut'),  # Pas de conflit de salle
        ]
    
    def clean(self):
        # Vérifier que l'heure de fin est après l'heure de début
        if self.heure_fin and self.heure_debut and self.heure_fin <= self.heure_debut:
            raise ValidationError("L'heure de fin doit être après l'heure de début")
        
        # Vérifier que la date d'examen correspond à la période de l'évaluation
        if self.evaluation and self.evaluation.periode:
            if not (self.evaluation.periode.date_debut <= self.date_examen <= self.evaluation.periode.date_fin):
                raise ValidationError("La date d'examen doit être dans la période de l'évaluation")
    
    def __str__(self):
        return f"{self.evaluation} - {self.salle} le {self.date_examen}"


class RepartitionExamen(SoftDeleteModel):
    """
    Répartition des élèves dans les salles pour un examen.
    Génération automatique avec répartition intelligente.
    """
    
    planification = models.ForeignKey(
        PlanificationExamen,
        on_delete=models.CASCADE,
        related_name='repartitions'
    )
    eleve = models.ForeignKey(
        Eleve,
        on_delete=models.CASCADE,
        related_name='repartitions_examen'
    )
    numero_place = models.IntegerField(
        help_text="Numéro de place assigné dans la salle"
    )
    zone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Zone dans la salle (ex: A, B, C)"
    )
    rangee = models.IntegerField(
        blank=True,
        null=True,
        help_text="Numéro de rangée"
    )
    colonne = models.IntegerField(
        blank=True,
        null=True,
        help_text="Numéro de colonne"
    )
    instructions_speciales = models.TextField(
        blank=True,
        null=True,
        help_text="Instructions spéciales pour cet élève (ex: besoin particulier)"
    )
    est_present = models.BooleanField(
        default=False,
        help_text="L'élève s'est présenté à l'examen"
    )
    heure_arrivee = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Heure d'arrivée de l'élève"
    )
    
    class Meta:
        db_table = 'academics_repartitionexamen'
        verbose_name = 'Répartition d\'Examen'
        verbose_name_plural = 'Répartitions d\'Examens'
        ordering = ['planification', 'numero_place']
        unique_together = [
            ('planification', 'eleve'),  # Un élève par planification
            ('planification', 'numero_place'),  # Une place par planification
        ]
        indexes = [
            models.Index(fields=['planification']),
            models.Index(fields=['eleve']),
            models.Index(fields=['numero_place']),
        ]
    
    def __str__(self):
        return f"{self.eleve} - Place {self.numero_place} ({self.planification.salle})"




