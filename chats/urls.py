from django.urls import path
from .views import (
    CreateSessionView,
    SessionListCreateView,
    SessionDetailView,
    ChatMessageView,
    ChatUpdateView
)

urlpatterns = [

    # 예: http://127.0.0.1:8000/api/sessions/1/chat/
    path('sessions',CreateSessionView.as_view(), name='CreateSessionView'),



    # 세션 관련
    path('sessions', SessionListCreateView.as_view(), name='session-list-create'),
    path('sessions/<int:session_id>', SessionDetailView.as_view(), name='session-detail'),

    # 메시지 조회 및 채팅 전송
    path('sessions/<int:session_id>/messages', ChatMessageView.as_view(), name='session-messages'),  # GET
    path('sessions/<int:session_id>/chat', ChatMessageView.as_view(), name='chat-send'),  # POST

    # 채팅 수정 (명세서의 /sessions/chats/{message_id} 준수)
    path('sessions/chats/<int:message_id>', ChatUpdateView.as_view(), name='chat-update'),
]

