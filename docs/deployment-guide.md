# Guide de deploiement

## Config generale

- Settings prod: `config/settings/prod.py`
- `DEBUG = False`
- Cookies securises (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- `ALLOWED_HOSTS` via env

## Services requis

- PostgreSQL (DB principale)
- Redis (cache + channels)
- Worker Celery + Celery Beat (si taches planifiees actives)

## Points d'entree

- WSGI: `config/wsgi.py`
- ASGI: `config/asgi.py` (requis pour WebSocket)

## Statique / media

- `STATIC_URL = /static/`
- `MEDIA_ROOT = BASE_DIR / media`

## Variables d'environnement minimales

- `SECRET_KEY`
- `DB_USER`
- `DB_NAME`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `ALLOWED_HOSTS`

## Notes

- Le middleware `AcademicYearCookieMiddleware` pose un cookie `academic_year_id`.
- WebSocket `ws/notifications/` exige une session authentifiee.
