from django.urls import path, include
from rest_framework.routers import DefaultRouter

from academics.views import AffectationViewSet, BulletinViewSet, ClasseViewSet, CoursViewSet, EvaluationViewSet, NoteViewSet
from academics.views.dashboard_views import TeacherDashboardView

router = DefaultRouter()

router.register("classes", ClasseViewSet, basename="classe")

router.register("cours", CoursViewSet, basename="cours")

router.register("affectations", AffectationViewSet, basename="affectation")

router.register("evaluations", EvaluationViewSet, basename="evaluation")

router.register("notes", NoteViewSet, basename="note")

router.register("bulletins", BulletinViewSet, basename="bulletin")


urlpatterns = [
    path("dashboard/teacher/", TeacherDashboardView.as_view(), name="teacher-dashboard"),
] + router.urls