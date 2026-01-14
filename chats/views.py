from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Session, Message
from .services import ChatService
from .serializers import AIChatResponseSerializer

class ChatAIView(APIView):
    def post(self, request, session_id):
        # 1. 세션 존재 확인 (Soft Delete 고려)
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        user_sentence = request.data.get("message")

        if not user_sentence:
            return Response({"error": "메시지 내용이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. 서비스 호출
        ai_message = ChatService.create_chat_pair(session, user_sentence)

        # 3. 공용 응답 규격 반환
        return Response({
            "status": "success",
            "code": "COMMON_201",
            "message": "AI 답변 생성 성공",
            "data": AIChatResponseSerializer(ai_message).data
        }, status=status.HTTP_201_CREATED)

    def patch(self, request, session_id=None, message_id=None):
        # URL에서 message_id가 안 넘어오면 Body에서라도 찾음
        target_id = message_id or request.data.get("message_id")
        new_content = request.data.get("message")

        if not target_id or not new_content:
            return Response({"error": "message_id와 message가 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 원본 유저 메시지 객체 가져오기 (삭제되지 않은 것만)
        original_user_msg = get_object_or_404(
            Message, id=target_id, role='user', is_deleted=False
        )
        session = original_user_msg.session

        # 2. 서비스 호출 (삭제 후 새로 생성하는 로직)
        new_ai_msg = ChatService.update_chat_by_replacement(session, original_user_msg, new_content)

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "메시지가 성공적으로 교체되었습니다.",
            "data": AIChatResponseSerializer(new_ai_msg).data
        }, status=status.HTTP_200_OK)