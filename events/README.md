# 📅 Module Events - Gestion des Événements et Actualités

## Vue d'ensemble

Le module **Events** permet de gérer les événements et actualités de l'école de manière complète et professionnelle.

### Fonctionnalités principales

✅ **Gestion des événements**
- Création et gestion d'événements scolaires
- Types variés (académique, sportif, culturel, etc.)
- Gestion des inscriptions aux événements
- Suivi des participants

✅ **Gestion des actualités**
- Publication d'actualités et annonces
- Système d'alertes importantes
- Épinglage de contenus
- Compteur de vues

---

## 📊 Modèles de données

### 1. Event (Événement)

Gestion complète des événements scolaires.

**Champs principaux:**
- `titre`: Titre de l'événement (200 caractères max)
- `description`: Description détaillée
- `type_evenement`: Type (academique, sportif, culturel, administratif, social, autre)
- `date_debut`: Date et heure de début
- `date_fin`: Date et heure de fin (optionnel)
- `lieu`: Lieu de l'événement
- `organisateur`: Utilisateur organisateur (FK User)
- `statut`: Statut (planifie, en_cours, termine, annule, reporte)
- `annee_academique`: Année académique (FK)
- `participants_attendus`: Nombre attendu
- `image`: Image de l'événement
- `est_public`: Visible publiquement
- `inscription_requise`: Inscription nécessaire

**Propriétés calculées:**
- `est_passe`: Vérifie si l'événement est passé
- `est_en_cours`: Vérifie si l'événement est en cours

### 2. Actualite (Actualité)

Publication d'actualités et annonces.

**Champs principaux:**
- `titre`: Titre (250 caractères max)
- `sous_titre`: Sous-titre (300 caractères max)
- `contenu`: Contenu complet (TextField)
- `categorie`: Catégorie (annonce, succes, info, alerte, nouveau, autre)
- `statut`: Statut (brouillon, publie, archive)
- `auteur`: Utilisateur auteur (FK User)
- `annee_academique`: Année académique (FK)
- `image_principale`: Image principale
- `fichier_joint`: Fichier joint (PDF, etc.)
- `est_une_alerte`: Marquer comme alerte importante
- `est_epingle`: Épingler en haut
- `date_publication`: Date de publication
- `date_expiration`: Date d'expiration
- `vues`: Compteur de vues
- `tags`: Tags (séparés par virgules)

**Propriétés calculées:**
- `est_active`: Vérifie si l'actualité est publiée et non expirée

**Méthodes:**
- `incrementer_vues()`: Incrémente le compteur
- `get_tags_list()`: Retourne la liste des tags

### 3. InscriptionEvenement

Gestion des inscriptions aux événements.

**Champs principaux:**
- `evenement`: Événement concerné (FK Event)
- `participant`: Utilisateur participant (FK User)
- `statut`: Statut (en_attente, confirme, annule)
- `nombre_accompagnants`: Nombre d'accompagnants
- `commentaire`: Commentaire

**Contraintes:**
- `unique_together`: (evenement, participant) - pas de doublon

---

## 🔌 API Endpoints

### Events (Événements)

| Méthode | Endpoint | Action | Permission |
|---------|----------|--------|------------|
| GET | `/api/events/evenements/` | Liste événements | Authenticated |
| POST | `/api/events/evenements/` | Créer événement | StaffOrDirector |
| GET | `/api/events/evenements/{id}/` | Détail événement | Authenticated |
| PUT/PATCH | `/api/events/evenements/{id}/` | Modifier événement | StaffOrDirector |
| DELETE | `/api/events/evenements/{id}/` | Supprimer événement | StaffOrDirector |
| GET | `/api/events/evenements/publics/` | Événements publics | **AllowAny** |
| GET | `/api/events/evenements/a_venir/` | Événements à venir | **AllowAny** |
| GET | `/api/events/evenements/passes/` | Événements passés | Authenticated |
| POST | `/api/events/evenements/{id}/inscrire/` | S'inscrire | Authenticated |
| GET | `/api/events/evenements/mes_inscriptions/` | Mes inscriptions | Authenticated |

### Actualités

| Méthode | Endpoint | Action | Permission |
|---------|----------|--------|------------|
| GET | `/api/events/actualites/` | Liste actualités | Authenticated |
| POST | `/api/events/actualites/` | Créer actualité | StaffOrDirector |
| GET | `/api/events/actualites/{id}/` | Détail actualité | Authenticated |
| PUT/PATCH | `/api/events/actualites/{id}/` | Modifier actualité | StaffOrDirector |
| DELETE | `/api/events/actualites/{id}/` | Supprimer actualité | StaffOrDirector |
| GET | `/api/events/actualites/publiques/` | Actualités publiées | **AllowAny** |
| GET | `/api/events/actualites/alertes/` | Alertes actives | **AllowAny** |
| POST | `/api/events/actualites/{id}/publier/` | Publier actualité | StaffOrDirector |
| POST | `/api/events/actualites/{id}/archiver/` | Archiver actualité | StaffOrDirector |

### Inscriptions

| Méthode | Endpoint | Action | Permission |
|---------|----------|--------|------------|
| GET | `/api/events/inscriptions/` | Liste inscriptions | Authenticated |
| GET | `/api/events/inscriptions/{id}/` | Détail inscription | Authenticated |
| POST | `/api/events/inscriptions/{id}/confirmer/` | Confirmer inscription | Authenticated |
| POST | `/api/events/inscriptions/{id}/annuler/` | Annuler inscription | Authenticated |

---

## 🎯 Exemples d'utilisation

### 1. Créer un événement

```python
POST /api/events/evenements/

{
    "titre": "Journée Portes Ouvertes 2026",
    "description": "Venez découvrir notre établissement...",
    "type_evenement": "social",
    "date_debut": "2026-04-15T09:00:00Z",
    "date_fin": "2026-04-15T17:00:00Z",
    "lieu": "Campus Principal",
    "annee_academique": 1,
    "participants_attendus": 200,
    "est_public": true,
    "inscription_requise": true
}
```

### 2. Publier une actualité

```python
POST /api/events/actualites/

{
    "titre": "Excellents résultats aux examens d'État",
    "sous_titre": "100% de réussite pour nos finalistes",
    "contenu": "Nous sommes fiers d'annoncer...",
    "categorie": "succes",
    "statut": "publie",
    "annee_academique": 1,
    "est_epingle": true,
    "tags": "succès, examens, résultats"
}
```

### 3. S'inscrire à un événement

```python
POST /api/events/evenements/1/inscrire/

{
    "nombre_accompagnants": 2,
    "commentaire": "Je viendrai avec mes deux enfants"
}
```

### 4. Consulter les événements publics (sans auth)

```python
GET /api/events/evenements/publics/
```

### 5. Consulter les alertes actives (sans auth)

```python
GET /api/events/actualites/alertes/

# Retourne max 5 alertes importantes actives
```

---

## 🔒 Permissions

### Événements
- **AllowAny**: `/publics/`, `/a_venir/`
- **IsAuthenticated**: `list`, `retrieve`, `mes_inscriptions`, `inscrire`
- **IsStaffOrDirector**: `create`, `update`, `destroy`

### Actualités
- **AllowAny**: `/publiques/`, `/alertes/`
- **IsAuthenticated**: `list`, `retrieve`
- **IsStaffOrDirector**: `create`, `update`, `destroy`, `publier`, `archiver`

### Inscriptions
- **IsAuthenticated**: Toutes les actions
- **Filtrage**: Les utilisateurs non-staff voient seulement leurs propres inscriptions

---

## 📈 Fonctionnalités avancées

### 1. Système d'alertes

Les actualités peuvent être marquées comme alertes (`est_une_alerte=True`):
- Affichées en priorité
- Limitées à 5 alertes actives simultanées
- Accessible sans authentification via `/alertes/`

### 2. Épinglage

Les actualités peuvent être épinglées (`est_epingle=True`):
- Toujours affichées en haut
- Utile pour les annonces importantes

### 3. Compteur de vues

Les actualités comptent automatiquement les vues:
- Incrémenté à chaque `retrieve()`
- Utilise la méthode `incrementer_vues()`

### 4. Gestion des inscriptions

Pour les événements avec inscription requise:
- Vérification automatique des doublons
- Validation des événements (pas passés, pas annulés)
- Confirmation/annulation possible

### 5. Tags

Les actualités supportent un système de tags:
- Stockés comme chaîne (séparés par virgules)
- Méthode `get_tags_list()` pour récupérer la liste
- Utile pour filtrage et recherche

---

## 🎨 Administration Django

### Actions en masse disponibles

**Actualités:**
- ✅ Publier les actualités sélectionnées
- ✅ Archiver les actualités sélectionnées

**Inscriptions:**
- ✅ Confirmer les inscriptions sélectionnées
- ✅ Annuler les inscriptions sélectionnées

### Filtres et recherche

**Événements:**
- Filtres: type, statut, visibilité, année
- Recherche: titre, description, lieu
- Hiérarchie: par date de début

**Actualités:**
- Filtres: catégorie, statut, alerte, épinglé, année
- Recherche: titre, sous-titre, contenu, tags
- Hiérarchie: par date de publication

---

## 🔄 Intégration avec autres modules

### Communication

Les événements et actualités peuvent déclencher des notifications:
```python
from communication.services.notification_service import NotificationService

# Notification lors de publication d'une actualité
NotificationService.send_notification(
    titre="Nouvelle actualité",
    message=actualite.titre,
    recipient_type='all'
)
```

### Core

Liaison avec les années académiques:
- Les événements sont liés à une année
- Les actualités sont liées à une année
- Filtrage automatique possible

### Common

Intégration avec le système d'audit:
- Toutes les actions sont loguées
- Traçabilité complète

---

## 📊 Statistiques disponibles

### Événements
- Nombre total d'événements par type
- Nombre de participants par événement
- Taux d'inscription

### Actualités
- Nombre de vues par actualité
- Actualités les plus populaires
- Répartition par catégorie

---

## ✅ Tests et validation

### Django check
```bash
$ python manage.py check
System check identified no issues (0 silenced).
```

### Migrations
```bash
$ python manage.py makemigrations events
Migrations for 'events':
  events\migrations\0001_initial.py
    + Create model Event (3 index)
    + Create model Actualite (4 index)
    + Create model InscriptionEvenement (1 contrainte unique)
```

---

## 🚀 Déploiement

### 1. Appliquer les migrations
```bash
python manage.py migrate events
```

### 2. Créer des données de test (optionnel)
```python
from events.models import Event, Actualite
from core.models import AnneeAcademique
from django.utils import timezone

# Créer un événement test
annee = AnneeAcademique.objects.first()
event = Event.objects.create(
    titre="Test Événement",
    description="Description test",
    type_evenement="academique",
    date_debut=timezone.now(),
    annee_academique=annee,
    est_public=True
)
```

### 3. Configurer les permissions
Les permissions sont déjà configurées via RBAC.

---

## 📝 Cas d'usage

### Scénario 1: Publication d'une actualité importante

1. **Création** (Staff/Director)
   ```
   POST /api/events/actualites/
   statut: "brouillon"
   ```

2. **Publication**
   ```
   POST /api/events/actualites/1/publier/
   → statut devient "publie"
   → date_publication remplie automatiquement
   ```

3. **Consultation publique**
   ```
   GET /api/events/actualites/publiques/
   → Visible par tous (même sans compte)
   ```

### Scénario 2: Organisation d'un événement avec inscriptions

1. **Création événement**
   ```json
   {
     "titre": "Réunion Parents-Professeurs",
     "type_evenement": "administratif",
     "inscription_requise": true,
     "est_public": false
   }
   ```

2. **Inscription d'un parent**
   ```
   POST /api/events/evenements/1/inscrire/
   ```

3. **Confirmation par admin**
   ```
   POST /api/events/inscriptions/1/confirmer/
   ```

---

## 🎯 Bonnes pratiques

### Publication d'actualités

✅ **À FAIRE:**
- Utiliser des titres courts et accrocheurs
- Ajouter des tags pertinents
- Définir une date d'expiration pour les infos temporaires
- Utiliser les alertes avec parcimonie

❌ **À ÉVITER:**
- Publier trop d'actualités épinglées
- Oublier d'archiver les anciennes actualités
- Ne pas remplir la description

### Gestion d'événements

✅ **À FAIRE:**
- Prévoir une date de fin pour les événements longs
- Activer `inscription_requise` pour contrôler les participants
- Mettre à jour le statut (planifie → en_cours → termine)
- Ajouter une image attractive

❌ **À ÉVITER:**
- Oublier de mettre à jour le statut
- Créer des événements sans année académique
- Oublier le lieu pour les événements physiques

---

## 📚 Documentation technique

### Structure du module

```
events/
├── __init__.py
├── admin.py              # Administration Django
├── apps.py               # Configuration de l'app
├── models.py             # Modèles (Event, Actualite, InscriptionEvenement)
├── serializers.py        # 8 serializers (dont publics)
├── urls.py               # Routes API
├── views.py              # 3 ViewSets avec 15+ actions
├── migrations/
│   └── 0001_initial.py  # Migration initiale
└── README.md             # Cette documentation
```

### Serializers disponibles

1. **EventSerializer** - Complet avec détails organisateur
2. **EventListSerializer** - Simplifié pour listes
3. **EventPublicSerializer** - Pour consultation publique
4. **ActualiteSerializer** - Complet avec détails auteur
5. **ActualiteListSerializer** - Simplifié pour listes
6. **ActualitePubliqueSerializer** - Pour consultation publique
7. **InscriptionEvenementSerializer** - Gestion inscriptions

### ViewSets et actions

#### EventViewSet
- **Standard**: list, create, retrieve, update, destroy
- **Custom**: publics, a_venir, passes, inscrire, mes_inscriptions

#### ActualiteViewSet
- **Standard**: list, create, retrieve, update, destroy
- **Custom**: publiques, publier, archiver, alertes

#### InscriptionEvenementViewSet
- **Standard**: list, retrieve
- **Custom**: confirmer, annuler

---

## 🎨 Intégration Frontend

### Endpoints publics (sans authentification)

Idéal pour afficher sur un site web public:

```javascript
// Récupérer les événements à venir
fetch('/api/events/evenements/publics/')
  .then(res => res.json())
  .then(events => console.log(events));

// Récupérer les actualités publiées
fetch('/api/events/actualites/publiques/')
  .then(res => res.json())
  .then(news => console.log(news));

// Récupérer les alertes importantes
fetch('/api/events/actualites/alertes/')
  .then(res => res.json())
  .then(alerts => console.log(alerts));
```

### Endpoints authentifiés

```javascript
// S'inscrire à un événement
fetch('/api/events/evenements/1/inscrire/', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer <token>',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    nombre_accompagnants: 2,
    commentaire: 'Je viendrai en famille'
  })
});
```

---

## 🏆 Résumé

### Statistiques du module

- **3 modèles** complets
- **8 serializers** (dont versions publiques)
- **3 ViewSets** avec 15+ actions personnalisées
- **3 admins Django** avec actions en masse
- **15+ endpoints API** documentés
- **Permissions RBAC** intégrées
- **Audit automatique** de toutes les actions

### Fonctionnalités clés

✅ Gestion complète des événements scolaires  
✅ Publication d'actualités avec système d'alertes  
✅ Inscriptions aux événements  
✅ Compteurs de vues automatiques  
✅ Endpoints publics pour site web  
✅ Administration intuitive  
✅ Intégration complète avec l'écosystème  

---

**Version:** 1.0.0  
**Date:** 2026-03-11  
**Status:** ✅ Production Ready
