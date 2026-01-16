from django.urls import path
from .views import PrecedentInitView, PrecedentListView, PrecedentDetailView

urlpatterns = [
    # 초기화 데이터
    path('init', PrecedentInitView.as_view(), name='precedent-init'),

    # 판례 목록 (검색 포함)
    path('', PrecedentListView.as_view(), name='precedent-list'),

    # 판례 상세 (<int:id>로 view의 id 인자와 매칭)
    path('<int:id>', PrecedentDetailView.as_view(), name='precedent-detail'),
]