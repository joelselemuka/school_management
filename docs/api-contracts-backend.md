# API Contracts (backend)

## Base URL

Routes principales montees dans `config/urls.py`:

- `/api/core/`
- `/api/academics/`
- `/api/admission/`
- `/api/accounts/`

`admin/` est disponible sur `/admin/`.

## Authentification

- Login: cookies `access_token` et `refresh_token` (SimpleJWT).
- Auth par cookie JWT via `CookieJWTAuthentication`.
- La plupart des endpoints exigent un utilisateur authentifie.

## Endpoints core

Base: `/api/core/`

- `GET /annees-academiques/`
- `POST /annees-academiques/`
- `GET /annees-academiques/{id}/`
- `PUT/PATCH /annees-academiques/{id}/`
- `DELETE /annees-academiques/{id}/`

- `GET /periodes/`
- `POST /periodes/`
- `GET /periodes/{id}/`
- `PUT/PATCH /periodes/{id}/`
- `DELETE /periodes/{id}/`

## Endpoints academics

Base: `/api/academics/`

ViewSets (CRUD standard):
- `classes`
- `cours`
- `affectations`
- `evaluations`
- `notes`
- `bulletins`

Endpoints typiques:
- `GET /{resource}/`
- `POST /{resource}/`
- `GET /{resource}/{id}/`
- `PUT/PATCH /{resource}/{id}/`
- `DELETE /{resource}/{id}/`

Custom actions:
- `POST /bulletins/generate/` (genere un bulletin)

## Endpoints admission

Base: `/api/admission/`

- `POST /bureau/` (inscription via bureau)

ViewSet `applications`:
- `GET /applications/`
- `POST /applications/`
- `GET /applications/{id}/`
- `PUT/PATCH /applications/{id}/`
- `DELETE /applications/{id}/`
- `POST /applications/{id}/approve/`
- `POST /applications/{id}/reject/`

Vue non branchee dans les urls:
- `OnlineAdmissionView` (non present dans `admission/urls.py`)

## Endpoints accounts (users)

Base: `/api/accounts/`

Auth:
- `POST /login/`
- `POST /logout/`
- `POST /refresh/`
- `GET /profile/`
- `PATCH /profile/`

Personnel:
- `GET /personnels/`
- `POST /personnels/`
- `GET /personnels/{id}/`
- `PUT/PATCH /personnels/{id}/`
- `DELETE /personnels/{id}/`

Parents:
- `GET /parents/`
- `POST /parents/`
- `GET /parents/{id}/`
- `PUT/PATCH /parents/{id}/`
- `DELETE /parents/{id}/`
- `POST /parents/{id}/add_student/`
- `POST /parents/{id}/remove_student/`
- `GET /parents/me/`

## WebSocket

- `ws/notifications/` (Channels)

## Routes definies mais non montees dans `config/urls.py`

Les fichiers suivants existent mais ne sont pas inclus dans `config/urls.py` (donc non exposes tant qu'ils ne sont pas ajoutes):

- `finance/urls.py` (frais, dettes, paiements, dashboard)
- `communication/urls.py` (notifications)
- `comptabilite/urls.py` (accounts, transactions, reports)

Si ces modules doivent etre exposes, il faut ajouter des `include(...)` correspondants dans `config/urls.py`.
