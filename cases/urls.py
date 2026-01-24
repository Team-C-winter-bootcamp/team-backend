from django.urls import path
from .views import CaseSearchView, PrecedentDetailView, CaseAnswerView

urlpatterns = [
    path('', CaseSearchView.as_view(), name='case_search'),
    path('<str:precedents_id>/answer/', CaseAnswerView.as_view(), name='case_answer'),
    path('<str:precedents_id>/', PrecedentDetailView.as_view(), name='precedent_detail'),
]
