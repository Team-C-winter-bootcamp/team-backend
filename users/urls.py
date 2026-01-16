from django.urls import path
from .views import TokenVerifyView, UserMeView, ClerkWebhookView

urlpatterns = [
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("me/", UserMeView.as_view(), name="user_me"),
    path("webhooks/clerk/", ClerkWebhookView.as_view(), name="clerk_webhook"),
]
