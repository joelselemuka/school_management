"""
URLs pour le module common (audit, documents).
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from common.views.audit_views import AuditLogViewSet, DocumentViewSet
from common.views.health_views import health, readiness, liveness, detailed

router = DefaultRouter()
router.register(r'audit-logs', AuditLogViewSet, basename='audit-log')
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
    path('health/', health, name='health'),
    path('health/ready/', readiness, name='health-readiness'),
    path('health/alive/', liveness, name='health-liveness'),
    path('health/detailed/', detailed, name='health-detailed'),
]
