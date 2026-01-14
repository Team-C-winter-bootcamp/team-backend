# chat_sessions/urls.py
from django.urls import path
from .views import ChatAIView  # 폴더 구조에 맞춰 import

urlpatterns = [
    # 예: http://127.0.0.1:8000/api/sessions/1/chat/
    path('/',Create_session.as_view(), name='create_session'),
    path('sessions/<int:session_id>/chat/', ChatAIView.as_view(), name='chat-post'),
    path('sessions/chats/<message_id>', ChatAIView.as_view(), name='chat-patch'),

]
