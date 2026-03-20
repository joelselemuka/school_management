# users/models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, AbstractUser

from django.conf import settings
from common.models import SoftDeleteModel
from django.core.exceptions import ValidationError
from django.db import transaction

from users.managers import EleveQuerySet, ParentQuerySet, PersonnelQuerySet, UserManager




class User(AbstractUser, PermissionsMixin,SoftDeleteModel):
    email = models.EmailField(unique=True,blank=True, null=True)
    username = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    phone = models.CharField(max_length=20, null=True, blank=True)
    photo = models.ImageField(upload_to="profiles/", null=True, blank=True)
    must_change_password = models.BooleanField(default=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    matricule = models.CharField(max_length=50, unique=True)
    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["matricule","email"]  # On peut ajouter d'autres champs requis ici
    
    objects = UserManager()
    
    def __str__(self):

        if self.username:
            return self.username

        if self.email:
            return self.email

        return f"User {self.pk}"
    
    def clean(self):

        if self.email == "":
            self.email = None
    
    def save(self, *args, **kwargs):

        if self.email:

            exists = User.objects.filter(
                    email=self.email
                ).exclude(pk=self.pk).exists()

            if exists:

                raise ValidationError(
                        "Cet email est déjà utilisé."
                    )

        super().save(*args, **kwargs)
    
    @property
    def is_student(self):

        return hasattr(self, "eleve_profile")


    @property
    def is_parent(self):

        return hasattr(self, "parent_profile")


    @property
    def is_personnel(self):

        return hasattr(self, "personnel_profile")
    
    
    @property
    def full_name(self):

        if self.first_name and self.last_name:

            return f"{self.first_name} {self.last_name}"

        if self.first_name:

            return self.first_name

        return self.username

    def get_short_name(self):

        return self.first_name
    
SEXE_CHOICES = [("masculin", "Masculin"), ("féminin", "Féminin")]


ELEVE_STATUS = [
    ("actif", "Actif"),
    ("renvoye", "Renvoyé"),
    ("diplome", "Diplômé"),
    ("transfere", "Transféré"),
    ("abandonne", "Abandonné"),
]




class Parent(SoftDeleteModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parent_profile")
    nom = models.CharField(max_length=100)
    postnom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    telephone = models.CharField(max_length=30, blank=True,null=True)
    adresse = models.TextField(blank=True,null=True)
    sexe = models.CharField(max_length=10, choices=SEXE_CHOICES)
    
    
    objects = ParentQuerySet.as_manager()
    def __str__(self):
        return f"{self.nom} {self.postnom} {self.prenom} "


class Eleve(SoftDeleteModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="eleve_profile")
    nom = models.CharField(max_length=100)
    postnom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=100, blank=True,null=True)
    adresse = models.TextField(blank=True,null=True)
    statut = models.CharField(max_length=20, choices=ELEVE_STATUS, default="actif")
    sexe = models.CharField(max_length=10, choices=SEXE_CHOICES, blank=True,null=True)
    
    objects = EleveQuerySet.as_manager()
    
    def __str__(self):
        return f"{self.nom} {self.postnom} {self.prenom} "
    
    
class ParentEleve(SoftDeleteModel):
    parent = models.ForeignKey(
        Parent,
        on_delete=models.CASCADE,
        related_name="enfants"
    )

    eleve = models.ForeignKey(
        Eleve,
        on_delete=models.CASCADE,
        related_name="parent_links"
    )
    relation = models.CharField(max_length=64, blank=True,null=True)  # "Mère", "Père", "Tuteur"
    reduction_percent = models.FloatField(default=0)
   
    objects = PersonnelQuerySet.as_manager()
   
    class Meta:
        unique_together = ("parent", "eleve")
        indexes = [
            models.Index(fields=["parent"]),
            models.Index(fields=["eleve"]),
        ]

    def __str__(self):
        return f"{self.parent} est {self.relation} de → {self.eleve}"
    
    
    
class PERSONNEL_FONCTION_CHOICES:
    # Si vous préférez une table séparée pour les fonctions, on peut remplacer ce champ
    # par une ForeignKey plus tard. Pour l'instant, on garde des choices simples.
    OPTIONS = [
        ("enseignant", "Enseignant"),
        ("comptable", "Comptable"),
        ("agent_entretien", "Agent d'entretien"),
        ("secretaire", "Secrétaire"),
        ("admin", "Administrateur"),
        ("bibliothecaire", "Bibliothécaire"),
        ("responsable_transport", "Responsable Transport"),
        ("autre", "Autre"),
    ]

class Personnel(SoftDeleteModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personnel_profile")
    fonction = models.CharField(max_length=32, choices=PERSONNEL_FONCTION_CHOICES.OPTIONS, default="enseignant")
    nom = models.CharField(max_length=100)
    postnom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    
    specialite = models.CharField(max_length=100, blank=True,null=True)
    telephone = models.CharField(max_length=30, blank=True,null=True)
    date_naissance = models.DateField(blank=True,null=True)
    lieu_naissance = models.CharField(max_length=100, blank=True,null=True)
    adresse = models.TextField(blank=True,null=True)
    # Note: on change le chemin upload_to vers personnel/ — les fichiers existants restent accessibles
   
    sexe = models.CharField(max_length=10, choices=SEXE_CHOICES, blank=True,null=True)
    

    def __str__(self):
        return f"{self.nom} {self.postnom} {self.prenom} "
    
    


    
    
    
    
    
    
    




