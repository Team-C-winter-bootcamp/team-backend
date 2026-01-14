from rest_framework.views import APIView
from rest_framework.response import Response

def ok(data, message="채팅 세션 목록을 성공적으로 가져왔습니다."):
    return Response(
        {
            "status": "success",
            "code": "COMMON_200",
            "message": message,
            "data": data,
        },
        status=200,
    )


def err(code, message, http_status):
    return Response(
        {
            "status": "error",
            "code": code,
            "message": message,
            "data": None,
        },
        status=http_status,
    )

# 요청 헤더에서 토큰만 뽑아옴
def get_bearer_token(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split("Bearer ", 1)[1].strip()
    return token or None


class SessionListView(APIView):
    def get(self, request):
        token = get_bearer_token(request)
        if not token:
            return err("ERR_401", "인증 토큰이 유효하지 않습니다. 다시 로그인해주세요.", 401)

        # 임시: token을 user key처럼 사용 (나중에 Clerk 검증으로 교체)
        clerk_user_id = token

        sessions = (
            Session.objects
            .filter(clerk_user_id=clerk_user_id)
            .order_by("-id")
        )

        data = [{"id": s.id, "title": s.title, "bookmark": s.bookmark} for s in sessions]
        return ok(data)

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
