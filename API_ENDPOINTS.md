# 📡 Documentation des API Endpoints

**Projet:** School Management System - API Backend  
**Date de génération:** 2026-03-11  
**Version:** v1

---

## 🎯 Vue d'Ensemble

Ce document liste tous les nouveaux endpoints API implémentés pour les fonctionnalités critiques du système.

**Base URL:** `/api/v1/`

**Authentication:** Toutes les routes requièrent l'authentification (Bearer Token ou Cookie-based JWT)

---

## 📚 Endpoints par Module

### 1. Module Examens et Salles (`/api/v1/academics/`)

#### 🏫 Salles (`/salles/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **GET** | `/salles/` | Liste toutes les salles | Authenticated |
| **POST** | `/salles/` | Crée une nouvelle salle | Admin/Staff |
| **GET** | `/salles/{id}/` | Détails d'une salle | Authenticated |
| **PUT** | `/salles/{id}/` | Modifie une salle | Admin/Staff |
| **PATCH** | `/salles/{id}/` | Modifie partiellement une salle | Admin/Staff |
| **DELETE** | `/salles/{id}/` | Supprime une salle (soft delete) | Admin |
| **GET** | `/salles/disponibles/` | Liste les salles disponibles | Authenticated |
| **GET** | `/salles/by_type/?type=examen` | Filtre par type de salle | Authenticated |

**Exemples de requêtes:**

```bash
# Créer une salle
POST /api/v1/academics/salles/
{
    "code": "A101",
    "nom": "Salle A101",
    "batiment": "Bâtiment A",
    "capacite": 40,
    "type_salle": "examen",
    "est_disponible": true
}

# Filtrer les salles disponibles avec capacité minimale
GET /api/v1/academics/salles/disponibles/?min_capacite=30
```

#### 📅 Sessions d'Examen (`/sessions-examen/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **GET** | `/sessions-examen/` | Liste toutes les sessions | Authenticated |
| **POST** | `/sessions-examen/` | Crée une session d'examen | Admin/Staff |
| **GET** | `/sessions-examen/{id}/` | Détails d'une session | Authenticated |
| **PUT/PATCH** | `/sessions-examen/{id}/` | Modifie une session | Admin/Staff |
| **DELETE** | `/sessions-examen/{id}/` | Supprime une session | Admin |
| **GET** | `/sessions-examen/by_periode/?periode_id=1` | Sessions par période | Authenticated |
| **GET** | `/sessions-examen/actives/` | Sessions actives | Authenticated |

**Exemple:**

```bash
# Créer une session d'examen
POST /api/v1/academics/sessions-examen/
{
    "nom": "Examens 1er Trimestre 2026",
    "periode": 1,
    "date_debut": "2026-04-01",
    "date_fin": "2026-04-15",
    "type_session": "examen_final",
    "statut": "planifie"
}
```

#### 🗓️ Planifications d'Examen (`/planifications-examen/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **GET** | `/planifications-examen/` | Liste toutes les planifications | Authenticated |
| **POST** | `/planifications-examen/` | Crée une planification | Admin/Staff |
| **GET** | `/planifications-examen/{id}/` | Détails d'une planification | Authenticated |
| **PUT/PATCH** | `/planifications-examen/{id}/` | Modifie une planification | Admin/Staff |
| **DELETE** | `/planifications-examen/{id}/` | Supprime une planification | Admin |
| **GET** | `/planifications-examen/by_evaluation/?evaluation_id=1` | Par évaluation | Authenticated |
| **GET** | `/planifications-examen/by_salle/?salle_id=1` | Par salle | Authenticated |
| **GET** | `/planifications-examen/{id}/summary/` | Résumé avec élèves | Authenticated |

**Exemple:**

```bash
# Planifier un examen
POST /api/v1/academics/planifications-examen/
{
    "evaluation": 123,
    "salle": 1,
    "date_examen": "2026-04-05",
    "heure_debut": "08:00",
    "heure_fin": "10:00",
    "duree_minutes": 120,
    "surveillants": [5, 12]
}

# Obtenir le résumé avec liste des élèves
GET /api/v1/academics/planifications-examen/1/summary/
```

#### 👥 Répartitions d'Élèves (`/repartitions-examen/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **GET** | `/repartitions-examen/` | Liste toutes les répartitions | Authenticated |
| **POST** | `/repartitions-examen/` | Crée une répartition manuelle | Staff |
| **GET** | `/repartitions-examen/{id}/` | Détails d'une répartition | Authenticated |
| **PUT/PATCH** | `/repartitions-examen/{id}/` | Modifie une répartition | Staff |
| **DELETE** | `/repartitions-examen/{id}/` | Supprime une répartition | Admin |
| **GET** | `/repartitions-examen/by_planification/?planification_id=1` | Par planification | Authenticated |
| **GET** | `/repartitions-examen/by_eleve/?eleve_id=1` | Par élève | Authenticated |
| **POST** | `/repartitions-examen/mark_present/` | Marque présence | Surveillant/Staff |

**Exemple:**

```bash
# Marquer un élève présent
POST /api/v1/academics/repartitions-examen/mark_present/
{
    "repartition_id": 45,
    "heure_arrivee": "2026-04-05T08:05:00Z"
}
```

#### 🤖 Génération Automatique (`/exam-distribution/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **POST** | `/exam-distribution/generate/` | Génère la répartition auto | Admin/Staff |
| **POST** | `/exam-distribution/validate/` | Valide avant génération | Admin/Staff |

**Exemple:**

```bash
# Générer automatiquement la répartition
POST /api/v1/academics/exam-distribution/generate/
{
    "evaluation_id": 123,
    "salle_ids": [1, 2, 3, 4],
    "max_students_per_class_per_room": 5,
    "spacing_strategy": "alternate",
    "clear_existing": true
}

# Réponse:
{
    "total_students": 120,
    "total_rooms": 4,
    "summary": [
        {
            "salle_code": "A101",
            "salle_nom": "Salle A101",
            "nombre_eleves": 30,
            "capacite": 40,
            "taux_occupation": 75.0
        },
        // ...
    ],
    "message": "Répartition générée avec succès: 120 élèves dans 4 salles"
}

# Valider avant de générer
POST /api/v1/academics/exam-distribution/validate/
{
    "evaluation_id": 123,
    "salle_ids": [1, 2]
}

# Réponse:
{
    "valid": true,
    "message": "Distribution possible",
    "total_students": 120,
    "total_capacity": 80,
    "rooms_needed": 4
}
```

---

### 2. Module Communication (`/api/v1/communication/`)

#### 💬 Salles de Chat (`/chat-rooms/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **GET** | `/chat-rooms/` | Liste toutes les rooms | Authenticated |
| **POST** | `/chat-rooms/` | Crée une room de chat | Authenticated |
| **GET** | `/chat-rooms/{id}/` | Détails d'une room | Member |
| **PUT/PATCH** | `/chat-rooms/{id}/` | Modifie une room | Admin/Moderator |
| **DELETE** | `/chat-rooms/{id}/` | Supprime une room | Admin |
| **GET** | `/chat-rooms/my_rooms/` | Mes rooms | Authenticated |
| **GET** | `/chat-rooms/by_classe/?classe_id=1` | Rooms par classe | Authenticated |
| **POST** | `/chat-rooms/{id}/add_member/` | Ajoute un membre | Admin/Moderator |
| **POST** | `/chat-rooms/{id}/remove_member/` | Retire un membre | Admin |
| **POST** | `/chat-rooms/{id}/mark_read/` | Marque comme lu | Member |

**Exemples:**

```bash
# Créer une room de classe
POST /api/v1/communication/chat-rooms/
{
    "nom": "6ème A - Chat",
    "type_room": "classe",
    "classe_id": 5,
    "description": "Chat de la classe 6ème A",
    "est_modere": true
}

# Créer un groupe privé
POST /api/v1/communication/chat-rooms/
{
    "nom": "Équipe Enseignants Math",
    "type_room": "groupe",
    "description": "Discussion entre profs de maths",
    "est_modere": false,
    "membre_ids": [10, 12, 15, 20]
}

# Mes rooms
GET /api/v1/communication/chat-rooms/my_rooms/

# Ajouter un membre
POST /api/v1/communication/chat-rooms/5/add_member/
{
    "user_id": 25,
    "role": "membre"
}

# Marquer les messages comme lus
POST /api/v1/communication/chat-rooms/5/mark_read/
```

#### 📨 Messages de Chat (`/chat-messages/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **GET** | `/chat-messages/` | Liste les messages | Authenticated |
| **POST** | `/chat-messages/` | Envoie un message | Member |
| **GET** | `/chat-messages/{id}/` | Détails d'un message | Member |
| **PUT/PATCH** | `/chat-messages/{id}/` | Modifie un message | Author |
| **DELETE** | `/chat-messages/{id}/` | Supprime un message | Author/Moderator |
| **GET** | `/chat-messages/by_room/?room_id=1` | Messages par room | Member |
| **POST** | `/chat-messages/{id}/moderate/` | Modère un message | Moderator/Admin |
| **GET** | `/chat-messages/pending_moderation/` | Messages en attente | Moderator |

**Exemples:**

```bash
# Envoyer un message texte
POST /api/v1/communication/chat-messages/
{
    "room": 5,
    "content": "Bonjour à tous!",
    "type_message": "text"
}

# Envoyer un fichier
POST /api/v1/communication/chat-messages/
{
    "room": 5,
    "content": "Voici le document demandé",
    "type_message": "file",
    "file_url": "https://s3.../document.pdf"
}

# Récupérer les messages d'une room (paginé)
GET /api/v1/communication/chat-messages/by_room/?room_id=5&page=1

# Modérer un message
POST /api/v1/communication/chat-messages/123/moderate/
{
    "is_moderated": true
}

# Messages en attente de modération
GET /api/v1/communication/chat-messages/pending_moderation/
```

#### 🔔 Préférences de Notification (`/notification-preferences/`)

| Méthode | Endpoint | Description | Permission |
|---------|----------|-------------|------------|
| **GET** | `/notification-preferences/my_preferences/` | Mes préférences | Authenticated |
| **PUT** | `/notification-preferences/my_preferences/` | Met à jour préférences | Authenticated |
| **PATCH** | `/notification-preferences/my_preferences/` | Modifie partiellement | Authenticated |

**Exemples:**

```bash
# Récupérer mes préférences
GET /api/v1/communication/notification-preferences/my_preferences/

# Mettre à jour les préférences
PATCH /api/v1/communication/notification-preferences/my_preferences/
{
    "email_enabled": true,
    "sms_enabled": false,
    "push_enabled": true,
    "notes_published": true,
    "absences": true,
    "paiements": true,
    "chat_messages": false,
    "digest_frequency": "daily",
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00"
}
```

---

## 🔑 Paramètres de Filtrage Communs

### Filtres Query Parameters

Tous les endpoints de liste supportent les paramètres suivants:

| Paramètre | Description | Exemple |
|-----------|-------------|---------|
| `search` | Recherche textuelle | `?search=math` |
| `ordering` | Tri | `?ordering=-created_at` |
| `page` | Pagination | `?page=2` |
| `page_size` | Taille de page | `?page_size=50` |

### Filtres Spécifiques

**Salles:**
- `type_salle`: `classe`, `examen`, `labo`, `amphi`
- `est_disponible`: `true`, `false`
- `min_capacite`: Nombre entier

**Sessions:**
- `periode`: ID de période
- `type_session`: `interrogation`, `examen_partiel`, `examen_final`
- `statut`: `planifie`, `en_cours`, `termine`

**Chat Rooms:**
- `type_room`: `classe`, `groupe`, `general`
- `classe`: ID de classe
- `actif`: `true`, `false`

**Chat Messages:**
- `room`: ID de room
- `sender`: ID d'utilisateur
- `type_message`: `text`, `file`, `image`, `system`
- `is_moderated`: `true`, `false`
- `is_deleted`: `true`, `false`

---

## 📊 Formats de Réponse

### Réponse de Liste (Paginée)

```json
{
    "count": 150,
    "next": "http://api.example.com/api/v1/academics/salles/?page=2",
    "previous": null,
    "results": [
        {
            "id": 1,
            "code": "A101",
            "nom": "Salle A101",
            // ...
        }
    ]
}
```

### Réponse de Succès

```json
{
    "id": 1,
    "code": "A101",
    "nom": "Salle A101",
    "capacite": 40,
    "created_at": "2026-03-11T10:00:00Z",
    "updated_at": "2026-03-11T10:00:00Z"
}
```

### Réponse d'Erreur

```json
{
    "error": "Message d'erreur descriptif"
}
```

ou

```json
{
    "field_name": ["Message d'erreur pour ce champ"]
}
```

---

## 🔒 Codes de Statut HTTP

| Code | Signification | Usage |
|------|---------------|-------|
| **200** | OK | Succès (GET, PUT, PATCH) |
| **201** | Created | Ressource créée (POST) |
| **204** | No Content | Suppression réussie (DELETE) |
| **400** | Bad Request | Données invalides |
| **401** | Unauthorized | Non authentifié |
| **403** | Forbidden | Permissions insuffisantes |
| **404** | Not Found | Ressource introuvable |
| **500** | Internal Server Error | Erreur serveur |

---

## 🧪 Exemples d'Utilisation Complets

### Scénario 1: Organiser un Examen de A à Z

```bash
# 1. Créer une session d'examen
POST /api/v1/academics/sessions-examen/
{
    "nom": "Examens Fin Trimestre 1",
    "periode": 1,
    "date_debut": "2026-04-01",
    "date_fin": "2026-04-10",
    "type_session": "examen_final"
}
# Réponse: {"id": 5, ...}

# 2. Vérifier les salles disponibles
GET /api/v1/academics/salles/disponibles/?min_capacite=30

# 3. Planifier l'examen de mathématiques
POST /api/v1/academics/planifications-examen/
{
    "evaluation": 45,
    "session_examen": 5,
    "salle": 3,
    "date_examen": "2026-04-05",
    "heure_debut": "08:00",
    "heure_fin": "10:00",
    "duree_minutes": 120,
    "surveillants": [10, 12]
}
# Réponse: {"id": 20, ...}

# 4. Valider la capacité pour la répartition auto
POST /api/v1/academics/exam-distribution/validate/
{
    "evaluation_id": 45,
    "salle_ids": [1, 2, 3, 4]
}

# 5. Générer la répartition automatique
POST /api/v1/academics/exam-distribution/generate/
{
    "evaluation_id": 45,
    "salle_ids": [1, 2, 3, 4],
    "max_students_per_class_per_room": 5,
    "spacing_strategy": "alternate"
}

# 6. Consulter le résumé de la planification
GET /api/v1/academics/planifications-examen/20/summary/

# 7. Le jour de l'examen, marquer les présences
POST /api/v1/academics/repartitions-examen/mark_present/
{
    "repartition_id": 150,
    "heure_arrivee": "2026-04-05T08:05:00Z"
}
```

### Scénario 2: Créer et Utiliser un Chat de Classe

```bash
# 1. Créer une room pour la classe
POST /api/v1/communication/chat-rooms/
{
    "nom": "6ème A - Discussions",
    "type_room": "classe",
    "classe_id": 8,
    "est_modere": true
}
# Réponse: {"id": 15, ...}

# 2. Ajouter des membres (enseignants, élèves)
POST /api/v1/communication/chat-rooms/15/add_member/
{
    "user_id": 50,
    "role": "moderateur"
}

# 3. Lister mes rooms
GET /api/v1/communication/chat-rooms/my_rooms/

# 4. Envoyer un message
POST /api/v1/communication/chat-messages/
{
    "room": 15,
    "content": "Bonjour la classe! N'oubliez pas l'examen de demain.",
    "type_message": "text"
}

# 5. Récupérer les messages de la room
GET /api/v1/communication/chat-messages/by_room/?room_id=15&page=1

# 6. Marquer comme lu
POST /api/v1/communication/chat-rooms/15/mark_read/

# 7. Modérer un message (si nécessaire)
POST /api/v1/communication/chat-messages/250/moderate/
{
    "is_moderated": true
}
```

---

## 📝 Notes Importantes

### Soft Delete
- Les ressources ne sont pas supprimées physiquement
- Le champ `actif` passe à `false`
- Les données restent accessibles pour audit

### Audit Log
- Toutes les actions critiques sont tracées automatiquement
- Informations enregistrées: user, IP, timestamp, changements

### Permissions RBAC
- Les permissions sont vérifiées automatiquement
- Matrice complète dans: `_bmad-output/implementation-artifacts/02-rbac-permissions-matrix.md`

### Performance
- Utilisation de `select_related()` et `prefetch_related()`
- Index sur les champs fréquemment filtrés
- Pagination activée par défaut

---

## 🔗 Ressources

- **Documentation BMAD Complète:** `_bmad-output/INDEX.md`
- **Spécifications OpenAPI:** `_bmad-output/planning-artifacts/openapi.yaml`
- **Guide d'Implémentation:** `_bmad-output/implementation-artifacts/01-implementation-guide.md`

---

**Généré le:** 2026-03-11  
**Version API:** v1  
**Status:** ✅ Endpoints implémentés et prêts à tester
