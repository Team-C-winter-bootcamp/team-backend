# chats/urls.py
from django.urls import path
from .views import SessionListView

urlpatterns = [
    path("sessions/", SessionListView.as_view(), name="session-list"),
]
