"""
Package de tests pour School Management System.

Structure:
- test_rbac.py - Tests permissions et filtrage
- test_api.py - Tests endpoints API
- test_models.py - Tests modèles
- test_services.py - Tests services métier
- test_celery.py - Tests tâches asynchrones
- test_websocket.py - Tests WebSocket

Exécution:
    python manage.py test
    python manage.py test tests.test_rbac
    pytest --cov=. --cov-report=html
"""
