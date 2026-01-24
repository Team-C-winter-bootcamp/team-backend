# from django.urls import path
# from .views import CaseSearchView, PrecedentDetailView, CaseAnswerView
# from documents.views import (
#     CaseDocumentCreateView,
#     CaseDocumentDetailView,
#     DocumentSessionCreateView,
#     DocumentSessionDetailView,
#     DocumentSessionMessageView,
#     DocumentSessionStreamView,
# )
#
# urlpatterns = [
#     path('', CaseSearchView.as_view(), name='case_search'),
#     path('<str:precedents_id>/answer/', CaseAnswerView.as_view(), name='case_answer'),
#     path('<str:precedents_id>/', PrecedentDetailView.as_view(), name='precedent_detail'),
# ]

from django.urls import path
from .views import CaseSearchView, PrecedentDetailView, CaseAnswerView
from documents.views import (
    CaseDocumentCreateView,
    CaseDocumentDetailView,
    DocumentSessionCreateView,
    DocumentSessionDetailView,
    DocumentSessionMessageView,
    DocumentSessionStreamView,
)

urlpatterns = [
    # 문서 생성 API (POST /api/cases/{case_id}/documents/) - 더 specific한 패턴 먼저
    path('<int:case_id>/documents/', CaseDocumentCreateView.as_view(), name='case_document_create'),
    # 문서 상세 조회 API
    path('<int:case_id>/documents/<int:document_id>/', CaseDocumentDetailView.as_view(), name='case_document_detail'),
    # 세션 기반 문서 작성 API
    path('<int:case_id>/document-sessions/', DocumentSessionCreateView.as_view(), name='document_session_create'),
    path('<int:case_id>/document-sessions/<uuid:session_id>/', DocumentSessionDetailView.as_view(), name='document_session_detail'),
    path('<int:case_id>/document-sessions/<uuid:session_id>/messages/', DocumentSessionMessageView.as_view(), name='document_session_message'),
    path('<int:case_id>/document-sessions/<uuid:session_id>/stream/', DocumentSessionStreamView.as_view(), name='document_session_stream'),
    path('', CaseSearchView.as_view(), name='case_search'),
    # 판례 조회 API
    path('<str:precedents_id>/answer/', CaseAnswerView.as_view(), name='case_answer'),
    path('<str:precedents_id>/', PrecedentDetailView.as_view(), name='precedent_detail'),
]