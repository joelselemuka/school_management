"""
URL configuration for config project.
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)


urlpatterns = [
    # Admin Django
    path('admin/', admin.site.urls),

    # ─── API v1 (versionnée) ─────────────────────────────────────────────────
    path('api/v1/core/', include('core.urls'), name="v1_core"),
    path('api/v1/academics/', include('academics.urls'), name="v1_academics"),
    path('api/v1/admission/', include('admission.urls'), name="v1_admission"),
    path('api/v1/accounts/', include('users.urls'), name="v1_accounts"),
    path('api/v1/finances/', include('finance.urls'), name="v1_finances"),
    path('api/v1/comptabilites/', include('comptabilite.urls'), name="v1_comptabilites"),
    path('api/v1/communications/', include('communication.urls'), name="v1_communications"),
    path('api/v1/attendances/', include('attendance.urls'), name="v1_attendances"),
    path('api/v1/common/', include('common.urls'), name="v1_common"),
    path('api/v1/events/', include('events.urls'), name="v1_events"),
    path('api/v1/paie/', include('paie.urls'), name="v1_paie"),
    path('api/v1/bibliotheque/', include('bibliotheque.urls'), name="v1_bibliotheque"),
    path('api/v1/transport/', include('transport.urls'), name="v1_transport"),

    # ─── API legacy (rétrocompatibilité) ────────────────────────────────────
    path('api/v1/paie/', include('paie.urls'), name="paie"),
    path('api/v1/core/', include('core.urls'), name="core"),
    path('api/v1/academics/', include('academics.urls'), name="academics"),
    path('api/v1/admission/', include('admission.urls'), name="admission"),
    path('api/v1/accounts/', include('users.urls'), name="accounts"),
    path('api/v1/finances/', include('finance.urls'), name="finances"),
    path('api/v1/comptabilites/', include('comptabilite.urls'), name="comptabilites"),
    path('api/v1/communications/', include('communication.urls'), name="communications"),
    path('api/v1/attendances/', include('attendance.urls'), name="attendances"),
    path('api/v1/common/', include('common.urls'), name="common"),
    path('api/v1/events/', include('events.urls'), name="events"),
    path('api/v1/bibliotheque/', include('bibliotheque.urls'), name="bibliotheque"),
    path('api/v1/transport/', include('transport.urls'), name="transport"),

    # Documentation API (drf-spectacular)
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/v1/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
        re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    ]
