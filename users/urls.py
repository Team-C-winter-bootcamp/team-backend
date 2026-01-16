from django.urls import path
from .views import TokenVerifyView,UserCheck

urlpatterns = [
    path("token/verify", TokenVerifyView.as_view(), name="token_verify"),
    path("me", UserCheck.as_view(), name="user_check"),
]
