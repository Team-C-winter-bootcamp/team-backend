from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import Session, Message
from .services import OllamaService
from .serializers import AIChatResponseSerializer


class ChatAIView(APIView):
    def post(self, request, session_id):
        user_sentence = request.data.get("message")

        try:
            session = Session.objects.get(id=session_id, is_deleted=False)

            # 1. 유저 메시지 저장
            last_order = session.messages.count()
            Message.objects.create(
                session=session,
                role='user',
                content=user_sentence,
                chat_order=last_order + 1
            )

            # 2. Ollama 호출 (Service Layer 사용)
            ai_content = OllamaService.ask_ai(user_sentence)

            # 3. AI 메시지 저장
            ai_message = Message.objects.create(
                session=session,
                role='assistant',
                content=ai_content,
                chat_order=last_order + 2
            )

            # 4. 요청하신 JSON 규격으로 응답 생성
            return Response({
                "status": "success",
                "code": "COMMON_201",
                "message": "AI가 답변에 성공하였습니다.",
                "data": AIChatResponseSerializer(ai_message).data
            }, status=status.HTTP_201_CREATED)

        except Session.DoesNotExist:
            return Response({"status": "error", "message": "세션을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)