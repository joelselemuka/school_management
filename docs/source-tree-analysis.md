# Analyse de l'arborescence

```
api_v3/
  manage.py                # entree CLI Django (settings dev par defaut)
  requirements.txt         # dependances Python
  PROJECT_CONTEXT.md       # contexte projet (existant)
  config/
    settings/
      base.py              # config commune
      dev.py               # config dev
      prod.py              # config prod
    urls.py                # routes principales
    asgi.py                # entree ASGI (Channels)
    wsgi.py                # entree WSGI
  common/
    authentication.py      # auth JWT via cookies
    permissions.py         # permissions custom
    middlewares.py         # AcademicYearCookieMiddleware
    models.py              # SoftDeleteModel, ActiveManager
  users/
    models.py              # User, Parent, Eleve, Personnel
    views.py               # login/logout/profile + ViewSets
    serializers.py
    services/
  core/
    models.py              # annee academique, periodes
    views.py               # ViewSets core
    serializers/
    services/
  academics/
    models.py              # classes, cours, evaluations, notes, bulletins
    views.py               # ViewSets + action generate bulletin
    serializers/
    services/
    permissions/
  admission/
    models.py              # inscriptions, candidatures
    views.py               # applications + bureau
    serializers/
    services/
    permissions/
  finance/
    models.py              # frais, dettes, paiements
    views.py               # ViewSets + dashboard
    serializers/
    services/
    permissions/
  comptabilite/
    models.py              # comptes, transactions, reports
    views.py               # ViewSets + reports
    serializers/
    services/
  attendance/
    models.py              # presence, horaires, discipline
    views.py               # (vide)
    services/
  communication/
    models.py              # notifications
    views.py               # preferences + marquer lu
    serializers.py
    routing.py             # WebSocket routes
  docs/
    project-scan-report.json
```

## Points a noter

- Les apps `finance`, `communication`, `comptabilite` ont des `urls.py` mais ne sont pas montees dans `config/urls.py`.
- `attendance/views.py` est vide (pas d'API exposee actuellement).
