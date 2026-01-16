from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Session, Message
from .services import ChatService
from .serializers import (
    AIChatResponseSerializer,
    ChatMessageRequestSerializer,
    ChatUpdateRequestSerializer
)
from .decorators import clerk_auth_required


class ChatMessageListView(APIView):
    @swagger_auto_schema(
        operation_summary="메시지 목록 조회",
        operation_description="특정 세션의 모든 메시지를 시간순으로 조회합니다. 경로: GET /sessions/{session_id}",
        tags=["채팅 메시지"],
        security=[{"Bearer": []}],
        manual_parameters=[
            openapi.Parameter(
                'session_id',
                openapi.IN_PATH,
                description="세션 ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="메시지 조회 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="COMMON_200"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="메시지 조회 성공"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                    "order": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                    "role": openapi.Schema(type=openapi.TYPE_STRING, example="user"),
                                    "content": openapi.Schema(type=openapi.TYPE_STRING, example="안녕하세요"),
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(description="인증 실패"),
            404: openapi.Response(description="세션을 찾을 수 없음")
        }
    )
    @clerk_auth_required
    def get(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, user=request.user, is_deleted=False)
        messages = Message.objects.filter(session=session, is_deleted=False).order_by("created_at")
        data = AIChatResponseSerializer(messages, many=True).data

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "메시지 조회 성공",
            "data": data
        }, status=status.HTTP_200_OK)


class ChatMessageSendView(APIView):
    @swagger_auto_schema(
        operation_summary="채팅 메시지 전송",
        operation_description="사용자 메시지를 전송하고 AI 응답을 생성합니다. 사용자 메시지와 AI 응답이 쌍으로 저장됩니다. 경로: POST /sessions/{session_id}/chat",
        tags=["채팅 메시지"],
        security=[{"Bearer": []}],
        manual_parameters=[
            openapi.Parameter(
                'session_id',
                openapi.IN_PATH,
                description="세션 ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        request_body=ChatMessageRequestSerializer,
        responses={
            201: openapi.Response(
                description="AI 답변 생성 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="COMMON_201"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="AI 답변 생성 성공"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=2),
                                "order": openapi.Schema(type=openapi.TYPE_INTEGER, example=2),
                                "role": openapi.Schema(type=openapi.TYPE_STRING, example="assistant"),
                                "content": openapi.Schema(type=openapi.TYPE_STRING, example="안녕하세요! 무엇을 도와드릴까요?"),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="메시지 내용이 없음"),
            401: openapi.Response(description="인증 실패"),
            404: openapi.Response(description="세션을 찾을 수 없음")
        }
    )
    @clerk_auth_required
    def post(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, user=request.user, is_deleted=False)
        user_sentence = request.data.get("message")

        if not user_sentence:
            return Response({
                "status": "error",
                "code": "ERR_400",
                "message": "메시지 내용이 없습니다."
            }, status=status.HTTP_400_BAD_REQUEST)

        ai_message = ChatService.create_chat_pair(session, user_sentence)

        return Response({
            "status": "success",
            "code": "COMMON_201",
            "message": "AI 답변 생성 성공",
            "data": AIChatResponseSerializer(ai_message).data
        }, status=status.HTTP_201_CREATED)


class ChatUpdateView(APIView):
    @swagger_auto_schema(
        operation_summary="채팅 메시지 수정",
        operation_description="기존 사용자 메시지를 수정하고, 해당 메시지와 연결된 AI 응답을 새로 생성합니다. 기존 메시지 쌍은 논리 삭제되고 새로운 메시지 쌍이 생성됩니다. 경로: PATCH /sessions/chats/{message_id}",
        tags=["채팅 메시지"],
        security=[{"Bearer": []}],
        manual_parameters=[
            openapi.Parameter(
                'message_id',
                openapi.IN_PATH,
                description="수정할 사용자 메시지 ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        request_body=ChatUpdateRequestSerializer,
        responses={
            200: openapi.Response(
                description="메시지 수정 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="COMMON_200"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="메시지가 성공적으로 교체되었습니다."),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=3),
                                "order": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                "role": openapi.Schema(type=openapi.TYPE_STRING, example="assistant"),
                                "content": openapi.Schema(type=openapi.TYPE_STRING, example="수정된 질문에 대한 답변"),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="메시지 내용이 없음"),
            401: openapi.Response(description="인증 실패"),
            404: openapi.Response(description="메시지를 찾을 수 없음")
        }
    )
    @clerk_auth_required
    def patch(self, request, message_id):
        new_content = request.data.get("message")
        if not new_content:
            return Response({
                "status": "error",
                "code": "ERR_400",
                "message": "수정할 메시지 내용이 필요합니다."
            }, status=status.HTTP_400_BAD_REQUEST)

        # [확인] session__user=request.user를 통해 관계형 조회 유지
        original_user_msg = get_object_or_404(
            Message, id=message_id, session__user=request.user, role='user', is_deleted=False
        )
        session = original_user_msg.session

        new_ai_msg = ChatService.update_chat_by_replacement(session, original_user_msg, new_content)

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "메시지가 성공적으로 교체되었습니다.",
            "data": AIChatResponseSerializer(new_ai_msg).data
        }, status=status.HTTP_200_OK)
