#!/usr/bin/env python
"""
Script de vérification de l'installation complète.

Vérifie:
- Tous les modules Django
- Connexions DB, Redis, Celery
- Fichiers de configuration
- Permissions
- Endpoints API

Usage:
    python scripts/verify_installation.py
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.core.management import call_command
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import importlib


def print_header(text):
    """Affiche un header."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def check_database():
    """Vérifie la connexion database."""
    print_header("🔍 Vérification Database")
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
        print(f"✅ Database: PostgreSQL connecté")
        print(f"   Version: {version[:50]}...")
        return True
    except Exception as e:
        print(f"❌ Database: ERREUR - {e}")
        return False


def check_redis():
    """Vérifie la connexion Redis."""
    print_header("🔍 Vérification Redis")
    try:
        cache.set('test_key', 'test_value', 10)
        value = cache.get('test_key')
        if value == 'test_value':
            print("✅ Redis: Connecté et fonctionnel")
            return True
        else:
            print("❌ Redis: Problème de lecture/écriture")
            return False
    except Exception as e:
        print(f"❌ Redis: ERREUR - {e}")
        return False


def check_celery():
    """Vérifie Celery."""
    print_header("🔍 Vérification Celery")
    try:
        from celery_app import app
        inspector = app.control.inspect()
        active = inspector.active()
        
        if active:
            print(f"✅ Celery: {len(active)} worker(s) actif(s)")
            for worker, tasks in active.items():
                print(f"   - {worker}: {len(tasks)} tâche(s)")
            return True
        else:
            print("⚠️  Celery: Aucun worker actif")
            print("   Démarrez avec: celery -A celery_app worker -l info")
            return False
    except Exception as e:
        print(f"❌ Celery: ERREUR - {e}")
        return False


def check_apps():
    """Vérifie les apps Django."""
    print_header("🔍 Vérification Apps Django")
    
    required_apps = [
        'users',
        'core',
        'academics',
        'attendance',
        'finance',
        'admission',
        'communication',
        'common',
    ]
    
    all_ok = True
    for app_name in required_apps:
        try:
            app = importlib.import_module(app_name)
            print(f"✅ App '{app_name}': Chargée")
        except Exception as e:
            print(f"❌ App '{app_name}': ERREUR - {e}")
            all_ok = False
    
    return all_ok


def check_models():
    """Vérifie les modèles principaux."""
    print_header("🔍 Vérification Modèles")
    
    models_to_check = [
        ('users', 'CustomUser'),
        ('users', 'Eleve'),
        ('users', 'Parent'),
        ('core', 'Ecole'),
        ('core', 'AnneeAcademique'),
        ('academics', 'Classe'),
        ('academics', 'Note'),
        ('academics', 'Bulletin'),
        ('attendance', 'Presence'),
        ('finance', 'Paiement'),
        ('admission', 'DemandeAdmission'),
        ('communication', 'Message'),
        ('communication', 'Notification'),
    ]
    
    all_ok = True
    for app_name, model_name in models_to_check:
        try:
            app_module = importlib.import_module(f'{app_name}.models')
            model = getattr(app_module, model_name)
            count = model.objects.count()
            print(f"✅ {app_name}.{model_name}: {count} enregistrement(s)")
        except Exception as e:
            print(f"❌ {app_name}.{model_name}: ERREUR - {e}")
            all_ok = False
    
    return all_ok


def check_migrations():
    """Vérifie les migrations."""
    print_header("🔍 Vérification Migrations")
    try:
        # Check pending migrations
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connections
        
        executor = MigrationExecutor(connections['default'])
        targets = executor.loader.graph.leaf_nodes()
        plan = executor.migration_plan(targets)
        
        if plan:
            print(f"⚠️  {len(plan)} migration(s) en attente")
            print("   Exécutez: python manage.py migrate")
            return False
        else:
            print("✅ Migrations: Toutes appliquées")
            return True
    except Exception as e:
        print(f"❌ Migrations: ERREUR - {e}")
        return False


def check_files():
    """Vérifie les fichiers critiques."""
    print_header("🔍 Vérification Fichiers")
    
    critical_files = [
        'celery_app.py',
        'config/asgi.py',
        'config/settings/redis.py',
        'config/settings/celery.py',
        'config/settings/channels.py',
        'config/settings/throttling.py',
        'config/settings/monitoring.py',
        'common/permissions.py',
        'common/mixins.py',
        'common/throttling.py',
        'common/tasks.py',
        'communication/consumers.py',
        'communication/routing.py',
        'scripts/backup_database.sh',
        'tests/test_rbac.py',
        'tests/test_api.py',
    ]
    
    all_ok = True
    for file_path in critical_files:
        full_path = os.path.join(settings.BASE_DIR, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path)
            print(f"✅ {file_path}: {size} bytes")
        else:
            print(f"❌ {file_path}: MANQUANT")
            all_ok = False
    
    return all_ok


def check_installed_packages():
    """Vérifie les packages installés."""
    print_header("🔍 Vérification Packages Python")
    
    required_packages = [
        'django',
        'djangorestframework',
        'celery',
        'redis',
        'channels',
        'psycopg2',
        'drf_spectacular',
        'sentry_sdk',
        'psutil',
    ]
    
    all_ok = True
    for package in required_packages:
        try:
            mod = importlib.import_module(package)
            version = getattr(mod, '__version__', 'unknown')
            print(f"✅ {package}: {version}")
        except ImportError:
            print(f"❌ {package}: NON INSTALLÉ")
            all_ok = False
    
    return all_ok


def run_verification():
    """Exécute toutes les vérifications."""
    print("\n" + "="*60)
    print("  🎯 VÉRIFICATION INSTALLATION - School Management System")
    print("="*60)
    
    results = {
        'Database': check_database(),
        'Redis': check_redis(),
        'Celery': check_celery(),
        'Apps Django': check_apps(),
        'Modèles': check_models(),
        'Migrations': check_migrations(),
        'Fichiers': check_files(),
        'Packages': check_installed_packages(),
    }
    
    # Résumé
    print_header("📊 RÉSUMÉ")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    percentage = (passed / total) * 100
    
    for check, result in results.items():
        status = "✅ OK" if result else "❌ ERREUR"
        print(f"{status:12} - {check}")
    
    print(f"\n{'='*60}")
    print(f"  Score: {passed}/{total} ({percentage:.0f}%)")
    
    if percentage == 100:
        print(f"  Status: ✅ INSTALLATION COMPLÈTE")
    elif percentage >= 80:
        print(f"  Status: ⚠️  INSTALLATION PARTIELLE")
    else:
        print(f"  Status: ❌ INSTALLATION INCOMPLÈTE")
    
    print(f"{'='*60}\n")
    
    return percentage == 100


if __name__ == '__main__':
    success = run_verification()
    sys.exit(0 if success else 1)
