from django.urls import path

from communication.views import MarkNotificationRead, NotificationPreferenceView, UserNotificationView
urlpatterns = [
    path("notifications/", UserNotificationView.as_view()),
    path("notifications/<int:pk>/read/", MarkNotificationRead.as_view()),
    path("notifications/preferences/", NotificationPreferenceView.as_view()),


]
