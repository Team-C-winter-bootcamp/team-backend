from django.urls import path
from .views import DocumentView

urlpatterns = [
    path('', DocumentView.as_view(), name='case_document_create'),
]
