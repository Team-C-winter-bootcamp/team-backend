from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Session, Message
from .services import ChatService
from .serializers import AIChatResponseSerializer, CreateSessionSerializer

def get_clerk_user_id(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.split("Bearer ", 1)[1].strip()


class CreateSessionView(APIView):
    @swagger_auto_schema(
        operation_summary="채팅 생성 API",
        operation_description="새로운 채팅 세션 생성",
        request_body=CreateSessionSerializer,
        manual_parameters=[
            openapi.Parameter(
                name='Authorization',
                in_=openapi.IN_HEADER,
                description='Bearer 토큰',
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            201: openapi.Response(
                description="채팅 생성 성공",
                examples={
                    "application/json": {
                        "status": "success",
                        "code": "COMMON_201",
                        "message": "새로운 채팅 세션이 생성되었습니다.",
                        "data": {"session_id": 123, "title": "임대차 계약 관련 상담"}
                    }
                }
            ),
            400: openapi.Response(
                description="첫 메시지 누락",
                examples={
                    "application/json": {
                        "status": "error",
                        "code": "ERR_400",
                        "message": "첫 메시지가 필요합니다."
                    }
                }
            ),
            401: openapi.Response(
                description="인증 토큰 없음",
                examples={
                    "application/json": {
                        "status": "error",
                        "code": "ERR_401",
                        "message": "인증 토큰이 필요합니다."
                    }
                }
            )
        }
    )
    def post(self, request):
        clerk_id = get_clerk_user_id(request)
        if not clerk_id:
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": "인증 토큰이 필요합니다."
            }, status=status.HTTP_401_UNAUTHORIZED)

        user_first_message = request.data.get("message")
        if not user_first_message:
            return Response({
                "status": "error",
                "code": "ERR_400",
                "message": "채팅을 시작할 메시지 내용이 필요합니다."
            }, status=status.HTTP_400_BAD_REQUEST)

        # 1. Ollama를 통해 제목 생성
        generated_title = ChatService.generate_session_title(user_first_message)

        # 2. 세션 생성
        session = Session.objects.create(
            clerk_user_id=clerk_id,
            title=generated_title,
            bookmark=False
        )

        return Response({
            "status": "success",
            "code": "COMMON_201",
            "message": "새로운 채팅 세션이 생성되었습니다.",
            "data": {"session_id": session.id, "title": session.title}
        }, status=status.HTTP_201_CREATED)
# --- 세션 리스트 조회 & 생성 ---
class SessionListCreateView(APIView):
    def get(self, request):
        clerk_id = get_clerk_user_id(request)
        if not clerk_id:
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": "인증 토큰이 필요합니다."
            }, status=status.HTTP_401_UNAUTHORIZED)

        sessions = Session.objects.filter(clerk_user_id=clerk_id, is_deleted=False).order_by("-id")
        data = [{"id": s.id, "title": s.title, "bookmark": s.bookmark} for s in sessions]

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "세션 목록 조회 성공",
            "data": data
        }, status=status.HTTP_200_OK)


# --- 세션 상세 ---
class SessionDetailView(APIView):
    def patch(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        title = request.data.get("title")
        bookmark = request.data.get("bookmark")

        if title is not None:
            session.title = title
        if bookmark is not None:
            session.bookmark = bookmark
        session.save()

        return Response({
            "status": "success",
            "code": "COMMON_201",
            "message": "세션 정보가 수정되었습니다.",
            "data": {"title": session.title, "bookmark": session.bookmark}
        }, status=status.HTTP_200_OK)

    def delete(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        session.is_deleted = True
        session.save()

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "세션이 삭제되었습니다.",
            "data": {"session_id": session.id, "title": session.title}
        }, status=status.HTTP_200_OK)


# --- 채팅 메시지 ---
class ChatMessageView(APIView):
    def get(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        messages = Message.objects.filter(session=session, is_deleted=False).order_by("created_at")
        data = AIChatResponseSerializer(messages, many=True).data

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "메시지 조회 성공",
            "data": data
        }, status=status.HTTP_200_OK)

    def post(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        user_sentence = request.data.get("message")
        if not user_sentence:
            return Response({"error": "메시지 내용이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

        ai_message = ChatService.create_chat_pair(session, user_sentence)
        return Response({
            "status": "success",
            "code": "COMMON_201",
            "message": "AI 답변 생성 성공",
            "data": AIChatResponseSerializer(ai_message).data
        }, status=status.HTTP_201_CREATED)


# --- 채팅 수정 ---
class ChatUpdateView(APIView):
    def patch(self, request, message_id):
        new_content = request.data.get("message")
        if not new_content:
            return Response({"error": "수정할 메시지 내용이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        original_user_msg = get_object_or_404(Message, id=message_id, role='user', is_deleted=False)
        session = original_user_msg.session

        new_ai_msg = ChatService.update_chat_by_replacement(session, original_user_msg, new_content)

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "메시지가 성공적으로 교체되었습니다.",
            "data": AIChatResponseSerializer(new_ai_msg).data
        }, status=status.HTTP_200_OK)
