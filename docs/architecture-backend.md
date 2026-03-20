# Architecture backend

## Style architectural

Monolithe Django organise par domaines fonctionnels (apps). Chaque app regroupe:

- `models.py`: persistance et regles de base
- `services/`: logique metier
- `serializers/`: mapping API
- `views.py`: endpoints DRF (ViewSet / APIView)
- `permissions/`: regles d'acces

## Flux de requete (HTTP)

1. Requete HTTP -> `config/urls.py`
2. Route vers `app.urls` (router DRF)
3. ViewSet/APIView
4. Services metiers
5. Model / ORM
6. Serializer -> reponse JSON

## Authentification et autorisation

- Auth via cookies JWT (`common.authentication.CookieJWTAuthentication`).
- JWT gere par SimpleJWT (access/refresh).
- Permissions custom dans `common.permissions` + permissions par app.

## Middleware

- `AcademicYearCookieMiddleware` fixe `request.academic_year` et pose un cookie `academic_year_id`.

## Realtime

- Channels active (ASGI).
- WebSocket `ws/notifications/` via `communication.routing`.
- Groupes par utilisateur: `user_{id}`.

## Asynchrone / planifie

- Celery + django-celery-beat + django_celery_results.
- Schedule dans `config/settings/base.py` (ex: `apply-penalties-every-night`).

## Configuration

- Settings par environnements: `config/settings/base.py`, `dev.py`, `prod.py`.
- Variables d'environnement via `python-decouple` (SECRET_KEY, DB_*).

## Points d'entree

- WSGI: `config/wsgi.py`
- ASGI: `config/asgi.py`
- CLI Django: `manage.py` (settings dev par defaut)
