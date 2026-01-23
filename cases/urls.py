from django.urls import path
from .views import CaseSearchView, PrecedentDetailView, CaseAnalysisView

urlpatterns = [
    path('', CaseSearchView.as_view(), name='case_search'),
    path('<int:cases_id>/<str:precedents_id>/', PrecedentDetailView.as_view(), name='precedent_detail'),
    path('<int:case_id>/<str:precedents_id>/answer/', CaseAnalysisView.as_view(), name='case_analysis'),
]
