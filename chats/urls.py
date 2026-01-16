from django.urls import path
from .session_views import (
    SessionListCreateView,
    SessionDetailView
)
from .message_views import (
    ChatMessageListView,
    ChatMessageSendView,
    ChatUpdateView
)

urlpatterns = [
    # 세션 관련
    path('sessions', SessionListCreateView.as_view(), name='session-list-create'),
    path('sessions/<int:session_id>', ChatMessageListView.as_view(), name='session-messages'),  # GET: 메시지 조회
    path('sessions/<int:session_id>/settings', SessionDetailView.as_view(), name='session-detail'),  # PATCH: 세션 수정, DELETE: 세션 삭제
    path('sessions/<int:session_id>/chat', ChatMessageSendView.as_view(), name='chat-send'),  # POST: 채팅 전송

    # 채팅 수정 (명세서의 /sessions/chats/{message_id} 준수)
    path('sessions/chats/<int:message_id>', ChatUpdateView.as_view(), name='chat-update'),
]                                                                                               