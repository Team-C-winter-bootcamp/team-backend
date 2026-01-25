from django.urls import path, re_path  # re_path 임포트
from .views import CaseSearchView, PrecedentDetailView, CaseAnswerView

urlpatterns = [
    path('', CaseSearchView.as_view(), name='case_search'),
    path('answer/<str:precedents_id>/', CaseAnswerView.as_view(), name='case_answer'),

    # <str:> 대신 re_path를 사용하여 한글과 숫자를 모두 허용하도록 수정
    re_path(r'^(?P<precedents_id>[^/]+)/?$', PrecedentDetailView.as_view(), name='precedent_detail'),
]