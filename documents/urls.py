from django.urls import path
from .views import DocumentGenerateView, DocumentGenerateFromSituationView

urlpatterns = [
    path('generate/', DocumentGenerateView.as_view(), name='document_generate'),
    path('generate-from-situation/', DocumentGenerateFromSituationView.as_view(), name='document_generate_from_situation'),
]
