from rest_framework.views import APIView
from rest_framework.response import Response

from .models import ChatSession


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
            ChatSession.objects
            .filter(clerk_user_id=clerk_user_id)
            .order_by("-id")
        )

        data = [{"id": s.id, "title": s.title, "bookmark": s.bookmark} for s in sessions]
        return ok(data)

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

<<<<<<< HEAD
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
=======
        except Session.DoesNotExist:
            return Response({"status": "error", "message": "세션을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
>>>>>>> 720e822143fbd18378afdaca781b4d3eedfef372
