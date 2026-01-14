from django.urls import path
from . import views

app_name = 'webhooks'

urlpatterns = [
    # /webhooks/clerk/
    path('clerk/', views.clerk_webhook, name='clerk-webhook'),
]
