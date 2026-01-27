from django.urls import path, re_path  # re_path 임포트
from .views import *

urlpatterns = [
    path('', CaseSearchView.as_view(), name='case_search'),
    # 'init/' 대신 정규표현식을 사용하여 슬래시 유무에 상관없이 대응
    re_path(r'^init/?$', InitDataAPIView.as_view(), name='init-data'), 
    path('<str:precedents_id>/', PrecedentDetailView.as_view(), name='precedent_detail'),
    path('answer/<str:precedents_id>/', CaseAnswerView.as_view(), name='case_answer'),
]
