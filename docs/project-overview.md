# Apercu du projet

## Resume

API backend Django pour la gestion d'etablissement scolaire (academics, admission, finance, comptabilite, attendance, communication, users). Architecture monolithique modulee par applications Django.

## Type de projet

- Type: backend (API Django/DRF)
- Repo: monolith
- Partie: backend

## Stack technique

| Categorie | Technologie | Version / Notes |
| --- | --- | --- |
| Langage | Python | venv local |
| Framework | Django | 5.2.11 |
| API | Django REST Framework | 3.16.1 |
| Auth | SimpleJWT + cookie JWT custom | cookies access/refresh |
| DB | PostgreSQL | via psycopg2-binary |
| Realtime | Django Channels + channels_redis | WebSocket notifications |
| Async | Celery + django-celery-beat + django_celery_results | taches planifiees |
| Cache | Redis + django-redis | cache / channel layer |
| CORS | django-cors-headers | dev: allow all |
| Utilitaires | python-decouple, django-filter | config/env, filtrage |

## Architecture (haut niveau)

- Monolithe Django avec apps par domaine: `academics`, `admission`, `attendance`, `communication`, `comptabilite`, `finance`, `users`, `core`, `common`.
- Couches classiques: models -> services -> serializers -> views (ViewSet/APIView).
- Auth via cookies JWT + permissions et roles custom.
- Realtime via Channels (WebSocket notifications).
- Taches planifiees via Celery beat.

## Apps principales

- `users`: comptes, profils (eleve, parent, personnel)
- `core`: annee academique, periodes, configuration ecole
- `academics`: classes, cours, evaluations, notes, bulletins
- `admission`: inscriptions, candidatures
- `finance`: frais, dettes, paiements
- `comptabilite`: comptes, ecritures, rapports
- `attendance`: presences, horaires, discipline
- `communication`: notifications et preferences
- `common`: permissions, middleware, auth, utils
