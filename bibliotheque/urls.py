from django.urls import path, include
from rest_framework.routers import DefaultRouter
from bibliotheque.views import (
    LivreViewSet, ExemplaireViewSet, EmpruntViewSet,
    PaiementAmendeViewSet, InventaireViewSet
)

router = DefaultRouter()
router.register(r'livres', LivreViewSet, basename='livres')
router.register(r'exemplaires', ExemplaireViewSet, basename='exemplaires')
router.register(r'emprunts', EmpruntViewSet, basename='emprunts')
router.register(r'amendes', PaiementAmendeViewSet, basename='amendes')
router.register(r'inventaires', InventaireViewSet, basename='inventaires')

urlpatterns = [
    path('', include(router.urls)),
]
