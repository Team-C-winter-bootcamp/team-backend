from django.urls import path
from .views import TokenVerifyView

urlpatterns = [
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
]
