from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Session, Message
from .services import ChatService
from .serializers import AIChatResponseSerializer


# 공통 유틸리티: 요청 헤더에서 Clerk 토큰(ID) 추출
def get_clerk_user_id(request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    return auth.split("Bearer ", 1)[1].strip()


# --- 세션 관련 View ---

class SessionListCreateView(APIView):
    """
    [GET] 사용자의 모든 채팅 세션 리스트 가져옴
    [POST] 새로운 채팅 세션 생성
    """

    def get(self, request):
        clerk_id = get_clerk_user_id(request)
        if not clerk_id:
            return Response({"status": "error", "code": "ERR_401", "message": "인증 토큰이 필요합니다."}, status=401)

        sessions = Session.objects.filter(clerk_user_id=clerk_id, is_deleted=False).order_by("-id")
        data = [{"id": s.id, "title": s.title, "bookmark": s.bookmark} for s in sessions]

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "세션 목록 조회 성공",
            "data": data
        }, status=200)

    def post(self, request):
        clerk_id = get_clerk_user_id(request)
        if not clerk_id:
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": "인증 토큰이 필요합니다."
            }, status=401)

        # 프론트에서 보낸 첫 메시지 추출
        user_first_message = request.data.get("message")

        if not user_first_message:
            return Response({
                "status": "error",
                "code": "ERR_400",
                "message": "채팅을 시작할 메시지 내용이 필요합니다."
            }, status=400)

        # 1. Ollama를 통해 제목 생성
        generated_title = ChatService.generate_session_title(user_first_message)

        # 2. 세션 생성
        session = Session.objects.create(
            clerk_user_id=clerk_id,
            title=generated_title,
            bookmark=False
        )

        # 3. 요청하신 규격대로 응답
        return Response({
            "status": "success",
            "code": "COMMON_201",
            "message": "새로운 채팅 세션이 생성되었습니다.",
            "data": {
                "session_id": session.id,
                "title": session.title,
            }
        }, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    """
    [PATCH] 세션 제목 변경 or 즐겨찾기 설정
    [DELETE] 세션 삭제 (Soft Delete)
    """

    def patch(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)

        title = request.data.get("title")
        bookmark = request.data.get("bookmark")

        if title is not None: session.title = title
        if bookmark is not None: session.bookmark = bookmark
        session.save()

        return Response({
            "status": "success", "code": "COMMON_201", "message": "세션 정보가 수정되었습니다.",
            "data": {"title": session.title, "bookmark": session.bookmark}
        }, status=201)

    def delete(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        session.is_deleted = True
        session.save()

        return Response({
            "status": "success", "code": "COMMON_200", "message": "세션이 삭제되었습니다.",
            "data": {"session_id": session.id, "title": session.title}
        }, status=200)


# --- 채팅 및 메시지 관련 View ---

class ChatMessageView(APIView):
    """
    [GET] 특정 세션의 메시지 목록 조회
    [POST] 질문 추가 및 AI 답변 받기
    """

    def get(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        messages = Message.objects.filter(session=session, is_deleted=False).order_by("created_at")

        # 프론트엔드 TS 타입을 고려한 데이터 구조화
        data = AIChatResponseSerializer(messages, many=True).data

        return Response({
            "status": "success", "code": "COMMON_200", "message": "메시지 조회 성공",
            "data": data
        }, status=200)

    def post(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, is_deleted=False)
        user_sentence = request.data.get("message")

        if not user_sentence:
            return Response({"error": "메시지 내용이 없습니다."}, status=400)

        ai_message = ChatService.create_chat_pair(session, user_sentence)

        return Response({
            "status": "success", "code": "COMMON_201", "message": "AI 답변 생성 성공",
            "data": AIChatResponseSerializer(ai_message).data
        }, status=201)


class ChatUpdateView(APIView):
    """
    [PATCH] 특정 채팅 수정 후 다시 답변 받기
    """

    def patch(self, request, message_id):
        new_content = request.data.get("message")
        if not new_content:
            return Response({"error": "수정할 메시지 내용이 필요합니다."}, status=400)

        original_user_msg = get_object_or_404(Message, id=message_id, role='user', is_deleted=False)
        session = original_user_msg.session

        new_ai_msg = ChatService.update_chat_by_replacement(session, original_user_msg, new_content)

        return Response({
            "status": "success", "code": "COMMON_200", "message": "메시지가 성공적으로 교체되었습니다.",
            "data": AIChatResponseSerializer(new_ai_msg).data
        }, status=200)