from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import Personnel, Parent, Eleve

User = get_user_model()


class Command(BaseCommand):

    help = "Créer des utilisateurs de test"

    def handle(self, *args, **kwargs):

        self.create_admin()
        self.create_teacher()
        self.create_parent()
        self.create_student()

        self.stdout.write(
            self.style.SUCCESS("Utilisateurs de test créés")
        )

    # -----------------
    # ADMIN
    # -----------------

    def create_admin(self):

        if User.objects.filter(username="admin").exists():
            return

        User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="password123",
            matricule="ADMIN001"
        )

    # -----------------
    # TEACHER
    # -----------------

    def create_teacher(self):

        if User.objects.filter(username="teacher").exists():
            return

        user = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="password123",
            matricule="ENS001"
        )

        Personnel.objects.create(
            user=user,
            nom="Teacher",
            prenom="Test",
            
        )

    # -----------------
    # PARENT
    # -----------------

    def create_parent(self):

        if User.objects.filter(username="parent").exists():
            return

        user = User.objects.create_user(
            username="parent",
            email="parent@test.com",
            password="password123",
            matricule="PAR001"
        )

        Parent.objects.create(
            user=user,
            nom="Parent",
            prenom="Test"
        )

    # -----------------
    # STUDENT
    # -----------------

    def create_student(self):

        if User.objects.filter(username="student").exists():
            return

        user = User.objects.create_user(
            username="student",
            password="password123",
            matricule="ELEVE001"
        )

        Eleve.objects.create(
            user=user,
            nom="Student",
            prenom="Test"
        )
        
        
        #468513450371380