# Guide de developpement (backend)

## Prerequis

- Python (env virtuel present dans `venv/`)
- PostgreSQL
- Redis (cache + channels)

Dependances:
- `requirements.txt`

## Variables d'environnement

Definies via `python-decouple`:

- `SECRET_KEY`
- `DB_USER`
- `DB_NAME`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `ALLOWED_HOSTS`

## Lancement local

Le projet utilise `config.settings.dev` par defaut (voir `manage.py`).

Commandes usuelles:

- `python manage.py migrate`
- `python manage.py runserver`

## Tests

Tests Django standard dans `*/tests.py`.

## Auth

- Login via `/api/accounts/login/` (cookies JWT).
- Refresh via `/api/accounts/refresh/`.

## Realtime (WebSocket)

- Route `ws/notifications/` (Channels).

## Taches planifiees

`CELERY_BEAT_SCHEDULE` defini dans `config/settings/base.py`.

## Import des seeds CSV

Le projet fournit des fichiers CSV de seed dans `_bmad-output/planning-artifacts/`.

Commandes:

- `python manage.py import_seed_csv`
- `python manage.py import_seed_csv --dir _bmad-output/planning-artifacts`
- `python manage.py import_seed_csv --only seed-users.csv seed-years.csv`
- `python manage.py import_seed_csv --dry-run`
- `python manage.py import_seed_csv --skip-existing`

Notes:

- `--strict` stoppe a la premiere erreur et rollback le fichier en cours.
- Sans `--strict`, un fichier avec erreurs est rollback et les fichiers suivants continuent.
- `--skip-existing` ignore les lignes deja presentes (pas de mise a jour).
- Validation stricte des colonnes obligatoires et types (date/decimal).
