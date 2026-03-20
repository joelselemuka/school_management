"""
Tests des endpoints API.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from core.models import AnneeAcademique, Periode
from academics.models import Classe

User = get_user_model()


class APIEndpointsTest(TestCase):
    """Tests des endpoints API principaux."""
    
    def setUp(self):
        """Setup initial."""
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='admin123',
            role='ADMIN'
        )
    
    def test_health_check_anonymous(self):
        """Health check accessible sans authentification."""
        response = self.client.get('/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)
    
    def test_api_requires_authentication(self):
        """API nécessite authentification."""
        response = self.client.get('/api/v1/academics/classes/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_jwt_authentication(self):
        """Test authentification JWT."""
        # Obtenir un token
        response = self.client.post('/api/v1/auth/token/', {
            'username': 'admin',
            'password': 'admin123'
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        
        token = response.data['access']
        
        # Utiliser le token
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/v1/academics/classes/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
    
    def test_pagination(self):
        """Test de la pagination."""
        self.client.force_authenticate(user=self.admin)
        
        # Créer 30 classes
        for i in range(30):
            Classe.objects.create(
                nom=f"Classe {i}",
                niveau="PRIMAIRE",
                capacite_max=30
            )
        
        # Requête sans pagination
        response = self.client.get('/api/v1/academics/classes/')
        
        # Vérifier la pagination
        self.assertIn('count', response.data)
        self.assertIn('results', response.data)
        self.assertEqual(len(response.data['results']), 20)  # Page size = 20
        
        # Page 2
        response = self.client.get('/api/v1/academics/classes/?page=2')
        self.assertEqual(len(response.data['results']), 10)  # 30 - 20 = 10
    
    def test_filtering(self):
        """Test des filtres."""
        self.client.force_authenticate(user=self.admin)
        
        # Créer des classes de différents niveaux
        Classe.objects.create(nom="1ère Primaire", niveau="PRIMAIRE", capacite_max=25)
        Classe.objects.create(nom="6ème Secondaire", niveau="SECONDAIRE", capacite_max=30)
        
        # Filtrer par niveau
        response = self.client.get('/api/v1/academics/classes/?niveau=PRIMAIRE')
        results = response.data.get('results', [])
        
        # Toutes les classes doivent être PRIMAIRE
        for classe in results:
            self.assertEqual(classe['niveau'], 'PRIMAIRE')
    
    def test_search(self):
        """Test de la recherche."""
        self.client.force_authenticate(user=self.admin)
        
        Classe.objects.create(nom="Mathématiques Spéciales", niveau="SECONDAIRE", capacite_max=20)
        Classe.objects.create(nom="Français Avancé", niveau="SECONDAIRE", capacite_max=20)
        
        # Rechercher "Math"
        response = self.client.get('/api/v1/academics/classes/?search=Math')
        results = response.data.get('results', [])
        
        # Devrait retourner la classe avec "Math"
        self.assertTrue(any('Math' in c['nom'] for c in results))
    
    def test_ordering(self):
        """Test du tri."""
        self.client.force_authenticate(user=self.admin)
        
        Classe.objects.create(nom="Classe A", niveau="PRIMAIRE", capacite_max=30)
        Classe.objects.create(nom="Classe B", niveau="PRIMAIRE", capacite_max=25)
        Classe.objects.create(nom="Classe C", niveau="PRIMAIRE", capacite_max=35)
        
        # Trier par capacité décroissante
        response = self.client.get('/api/v1/academics/classes/?ordering=-capacite_max')
        results = response.data.get('results', [])
        
        if len(results) >= 2:
            # Vérifier l'ordre
            self.assertGreaterEqual(
                results[0]['capacite_max'],
                results[1]['capacite_max']
            )


class CRUDOperationsTest(TestCase):
    """Tests des opérations CRUD."""
    
    def setUp(self):
        """Setup."""
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username='admin',
            password='admin123',
            role='ADMIN'
        )
        self.client.force_authenticate(user=self.admin)
    
    def test_create_classe(self):
        """Test création d'une classe."""
        data = {
            'nom': 'Test Classe',
            'niveau': 'PRIMAIRE',
            'capacite_max': 25
        }
        
        response = self.client.post('/api/v1/academics/classes/', data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['nom'], 'Test Classe')
    
    def test_update_classe(self):
        """Test mise à jour d'une classe."""
        classe = Classe.objects.create(
            nom="Classe Test",
            niveau="PRIMAIRE",
            capacite_max=25
        )
        
        data = {'capacite_max': 30}
        response = self.client.patch(f'/api/v1/academics/classes/{classe.id}/', data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['capacite_max'], 30)
    
    def test_delete_classe(self):
        """Test suppression d'une classe."""
        classe = Classe.objects.create(
            nom="Classe à Supprimer",
            niveau="PRIMAIRE",
            capacite_max=25
        )
        
        response = self.client.delete(f'/api/v1/academics/classes/{classe.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        
        # Vérifier suppression
        self.assertFalse(Classe.objects.filter(id=classe.id).exists())


# Exécuter avec:
# python manage.py test tests.test_api
