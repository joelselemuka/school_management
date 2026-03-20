"""
Tests du système RBAC (Role-Based Access Control).

Ces tests vérifient:
- Les permissions par rôle
- Le filtrage automatique des données
- Les restrictions d'accès
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from users.models import Eleve, Parent, Enseignant, ParentEleve
from academics.models import Classe, Cours, Note, Evaluation
from core.models import AnneeAcademique, Periode

User = get_user_model()


class RBACPermissionsTest(TestCase):
    """Tests des permissions RBAC."""
    
    def setUp(self):
        """Setup initial pour les tests."""
        self.client = APIClient()
        
        # Créer une année académique
        self.annee = AnneeAcademique.objects.create(
            nom="2025-2026",
            date_debut="2025-09-01",
            date_fin="2026-06-30",
            actif=True
        )
        
        # Créer une période
        self.periode = Periode.objects.create(
            nom="1er Trimestre",
            annee_academique=self.annee,
            date_debut="2025-09-01",
            date_fin="2025-12-15",
            actif=True
        )
        
        # Créer des utilisateurs de différents rôles
        self.admin = User.objects.create_user(
            username='admin',
            password='test123',
            role='ADMIN',
            is_staff=True
        )
        
        self.teacher = User.objects.create_user(
            username='teacher',
            password='test123',
            role='TEACHER'
        )
        
        self.parent = User.objects.create_user(
            username='parent',
            password='test123',
            role='PARENT'
        )
        
        self.student = User.objects.create_user(
            username='student',
            password='test123',
            role='STUDENT'
        )
        
        # Créer des données de test
        self.classe = Classe.objects.create(
            nom="6ème A",
            niveau="SECONDAIRE",
            capacite_max=30
        )
        
        # Créer un élève lié au student
        self.eleve = Eleve.objects.create(
            user=self.student,
            nom="Test",
            postnom="Student",
            prenom="John",
            sexe="M"
        )
        
        # Créer un parent lié
        self.parent_profile = Parent.objects.create(
            user=self.parent,
            nom="Parent",
            prenom="Test"
        )
        
        # Lier parent-élève
        ParentEleve.objects.create(
            parent=self.parent_profile,
            eleve=self.eleve,
            lien_parente="PERE"
        )
        
        # Créer une note
        self.cours = Cours.objects.create(
            nom="Mathématiques",
            code="MATH",
            credits=4
        )
        
        self.evaluation = Evaluation.objects.create(
            nom="Interro 1",
            cours=self.cours,
            classe=self.classe,
            periode=self.periode,
            date_evaluation=self.periode.date_debut,
            note_sur=20,
            type_evaluation="INTERRO"
        )
        
        self.note = Note.objects.create(
            evaluation=self.evaluation,
            eleve=self.eleve,
            note=15.0,
            published=True
        )
    
    def test_admin_can_see_all_notes(self):
        """Admin peut voir toutes les notes."""
        self.client.force_authenticate(user=self.admin)
        response = self.client.get('/api/v1/academics/notes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin voit toutes les notes
        self.assertGreaterEqual(len(response.data.get('results', [])), 1)
    
    def test_parent_can_only_see_own_children_notes(self):
        """Parent ne voit que les notes de ses enfants."""
        self.client.force_authenticate(user=self.parent)
        response = self.client.get('/api/v1/academics/notes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        
        # Vérifier que toutes les notes appartiennent à ses enfants
        for note in results:
            self.assertEqual(note['eleve']['id'], self.eleve.id)
    
    def test_student_can_only_see_own_notes(self):
        """Étudiant ne voit que ses propres notes."""
        self.client.force_authenticate(user=self.student)
        response = self.client.get('/api/v1/academics/notes/')
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data.get('results', [])
        
        # Vérifier que toutes les notes lui appartiennent
        for note in results:
            self.assertEqual(note['eleve']['id'], self.eleve.id)
    
    def test_parent_cannot_see_other_students_notes(self):
        """Parent ne peut pas accéder aux notes d'autres élèves."""
        # Créer un autre élève
        other_student = User.objects.create_user(
            username='other_student',
            role='STUDENT'
        )
        other_eleve = Eleve.objects.create(
            user=other_student,
            nom="Other",
            postnom="Student",
            prenom="Jane",
            sexe="F"
        )
        
        other_note = Note.objects.create(
            evaluation=self.evaluation,
            eleve=other_eleve,
            note=18.0,
            published=True
        )
        
        # Le parent essaie d'accéder
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f'/api/v1/academics/notes/{other_note.id}/')
        
        # Devrait retourner 404 (pas 403 pour ne pas révéler l'existence)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
    
    def test_student_cannot_create_note(self):
        """Étudiant ne peut pas créer de note."""
        self.client.force_authenticate(user=self.student)
        
        data = {
            'evaluation': self.evaluation.id,
            'eleve': self.eleve.id,
            'note': 20.0
        }
        
        response = self.client.post('/api/v1/academics/notes/', data)
        
        # Permission refusée
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
    
    def test_parent_can_view_but_not_modify(self):
        """Parent peut lire mais pas modifier."""
        self.client.force_authenticate(user=self.parent)
        
        # Lecture OK
        response = self.client.get(f'/api/v1/academics/notes/{self.note.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Modification KO
        data = {'note': 20.0}
        response = self.client.patch(f'/api/v1/academics/notes/{self.note.id}/', data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ThrottlingTest(TestCase):
    """Tests du rate limiting."""
    
    def setUp(self):
        """Setup initial."""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='test123',
            role='STUDENT'
        )
    
    def test_anonymous_rate_limit(self):
        """Utilisateur anonyme a une limite basse."""
        # Faire plus de 100 requêtes (limite anonyme)
        for i in range(105):
            response = self.client.get('/api/v1/core/ecoles/')
            
            if i >= 100:
                # Devrait être throttled
                self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
                break
    
    def test_authenticated_higher_limit(self):
        """Utilisateur authentifié a une limite plus élevée."""
        self.client.force_authenticate(user=self.user)
        
        # Les utilisateurs authentifiés ont 1000 req/h
        response = self.client.get('/api/v1/core/ecoles/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class DataFilteringTest(TestCase):
    """Tests du filtrage automatique des données."""
    
    def setUp(self):
        """Setup initial."""
        self.client = APIClient()
        
        # Créer année et période
        self.annee = AnneeAcademique.objects.create(
            nom="2025-2026",
            date_debut="2025-09-01",
            date_fin="2026-06-30",
            actif=True
        )
        
        # Créer 2 parents avec leurs enfants
        self.parent1 = User.objects.create_user(
            username='parent1',
            password='test123',
            role='PARENT'
        )
        
        self.parent2 = User.objects.create_user(
            username='parent2',
            password='test123',
            role='PARENT'
        )
        
        # Élèves
        self.student1 = User.objects.create_user(
            username='student1',
            role='STUDENT'
        )
        self.eleve1 = Eleve.objects.create(
            user=self.student1,
            nom="Eleve1",
            sexe="M"
        )
        
        self.student2 = User.objects.create_user(
            username='student2',
            role='STUDENT'
        )
        self.eleve2 = Eleve.objects.create(
            user=self.student2,
            nom="Eleve2",
            sexe="F"
        )
        
        # Liens parent-enfant
        parent1_profile = Parent.objects.create(
            user=self.parent1,
            nom="Parent1"
        )
        ParentEleve.objects.create(
            parent=parent1_profile,
            eleve=self.eleve1
        )
        
        parent2_profile = Parent.objects.create(
            user=self.parent2,
            nom="Parent2"
        )
        ParentEleve.objects.create(
            parent=parent2_profile,
            eleve=self.eleve2
        )
    
    def test_parent_data_isolation(self):
        """Parent 1 ne voit pas les données de Parent 2."""
        # Parent1 se connecte
        self.client.force_authenticate(user=self.parent1)
        response = self.client.get('/api/v1/users/eleves/')
        
        results = response.data.get('results', [])
        
        # Parent1 ne devrait voir que eleve1
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.eleve1.id)
        
        # Essayer d'accéder à eleve2 directement
        response = self.client.get(f'/api/v1/users/eleves/{self.eleve2.id}/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


# Exécuter les tests avec:
# python manage.py test tests.test_rbac
# python manage.py test tests.test_rbac.RBACPermissionsTest
# python manage.py test tests.test_rbac.RBACPermissionsTest.test_admin_can_see_all_notes
