from django.urls import path
from .views import  LoginView, LogoutView, ParentViewSet,  ProfileView, RefreshView, MyDashboardView

urlpatterns = [
    path("login/", LoginView.as_view()),
    path("logout/", LogoutView.as_view()),
    path("profile/", ProfileView.as_view()),
    path("refresh/", RefreshView.as_view()),
    path("me/dashboard/", MyDashboardView.as_view(), name='mega-dashboard'),
    

]

from rest_framework.routers import DefaultRouter
from .views import PersonnelViewSet
router = DefaultRouter()

router.register("personnels", PersonnelViewSet, basename="personnel")
router.register(

    "parents",

    ParentViewSet,

    basename="parent"

)


urlpatterns += router.urls

