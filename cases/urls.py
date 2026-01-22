from django.urls import path
from .views import HelloCasesView, RAGIngestView, RAGSearchView

urlpatterns = [
    path('hello/', HelloCasesView.as_view(), name='hello_cases'),
    path('rag-ingest/', RAGIngestView.as_view(), name='rag_ingest'),
    path('rag-search/', RAGSearchView.as_view(), name='rag_search'),
]
