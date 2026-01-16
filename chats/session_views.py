from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Session
from .services import ChatService
from .serializers import SessionCreateRequestSerializer, SessionUpdateRequestSerializer
from .decorators import clerk_auth_required


class SessionListCreateView(APIView):
    @swagger_auto_schema(
        operation_summary="세션 목록 조회",
        operation_description="현재 사용자의 모든 채팅 세션 목록을 조회합니다. 경로: GET /sessions",
        tags=["채팅 세션"],
        security=[{"Bearer": []}],
        responses={
            200: openapi.Response(
                description="세션 목록 조회 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="COMMON_200"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="세션 목록 조회 성공"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                    "title": openapi.Schema(type=openapi.TYPE_STRING, example="법률 상담"),
                                    "bookmark": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=False),
                                }
                            )
                        )
                    }
                )
            ),
            401: openapi.Response(description="인증 실패")
        }
    )
    @clerk_auth_required
    def get(self, request):
        # [확인] ForeignKey 명칭이 user이므로 user=request.user 사용 가능
        sessions = Session.objects.filter(user=request.user, is_deleted=False).order_by("-id")
        data = [{"id": s.id, "title": s.title, "bookmark": s.bookmark} for s in sessions]

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "세션 목록 조회 성공",
            "data": data
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="새 세션 생성",
        operation_description="첫 메시지를 입력하여 새로운 채팅 세션을 생성합니다. 메시지 내용을 기반으로 AI가 세션 제목을 자동 생성합니다. 경로: POST /sessions",
        tags=["채팅 세션"],
        security=[{"Bearer": []}],
        request_body=SessionCreateRequestSerializer,
        responses={
            201: openapi.Response(
                description="세션 생성 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="COMMON_201"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="새로운 채팅 세션이 생성되었습니다."),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "session_id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                "title": openapi.Schema(type=openapi.TYPE_STRING, example="법률 상담"),
                                "ai_response": openapi.Schema(type=openapi.TYPE_STRING, example="AI 답변 내용입니다."),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="메시지 내용이 없음"),
            401: openapi.Response(description="인증 실패")
        }
    )
    @clerk_auth_required
    def post(self, request):
        user_first_message = request.data.get("message")
        if not user_first_message:
            return Response({
                "status": "error",
                "code": "ERR_400",
                "message": "메시지 내용이 필요합니다."
            }, status=status.HTTP_400_BAD_REQUEST)

        generated_title = ChatService.generate_session_title(user_first_message)

        # [수정] 모델 필드명이 user(ForeignKey)이므로 객체 자체를 넘겨주는 것이 장고 표준입니다.
        session = Session.objects.create(
            user=request.user,  # user_id=request.user.id 대신 user 객체 전달
            title=generated_title,
            bookmark=False
        )

        # 세션 생성 시 첫 메시지와 AI 답변도 함께 생성
        ai_message = ChatService.create_chat_pair(session, user_first_message)

        return Response({
            "status": "success",
            "code": "COMMON_201",
            "message": "새로운 채팅 세션이 생성되었습니다.",
            "data": {
                "session_id": session.id,
                "title": session.title,
                "ai_response": ai_message.content,
            }
        }, status=status.HTTP_201_CREATED)


class SessionDetailView(APIView):
    @swagger_auto_schema(
        operation_summary="세션 정보 수정",
        operation_description="세션의 제목이나 북마크 상태를 수정합니다. 경로: PATCH /sessions/{session_id}/settings",
        tags=["채팅 세션"],
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
        request_body=SessionUpdateRequestSerializer,
        responses={
            200: openapi.Response(
                description="세션 수정 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="COMMON_200"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="세션 정보가 수정되었습니다."),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "title": openapi.Schema(type=openapi.TYPE_STRING, example="수정된 제목"),
                                "bookmark": openapi.Schema(type=openapi.TYPE_BOOLEAN, example=True),
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="잘못된 요청"),
            401: openapi.Response(description="인증 실패"),
            404: openapi.Response(description="세션을 찾을 수 없음")
        }
    )
    @clerk_auth_required
    def patch(self, request, session_id):
        # 본인 확인 로직 유지
        session = get_object_or_404(Session, id=session_id, user=request.user, is_deleted=False)

        title = request.data.get("title")
        bookmark = request.data.get("bookmark")

        if title is not None: session.title = title
        if bookmark is not None: session.bookmark = bookmark
        session.save()

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "세션 정보가 수정되었습니다.",
            "data": {"title": session.title, "bookmark": session.bookmark}
        }, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        operation_summary="세션 삭제",
        operation_description="세션을 논리 삭제(soft delete)합니다. 실제로는 is_deleted 플래그만 변경됩니다. 경로: DELETE /sessions/{session_id}/settings",
        tags=["채팅 세션"],
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
                description="세션 삭제 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "status": openapi.Schema(type=openapi.TYPE_STRING, example="success"),
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="COMMON_200"),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="세션이 삭제되었습니다."),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "session_id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                "title": openapi.Schema(type=openapi.TYPE_STRING, example="삭제된 세션"),
                            }
                        )
                    }
                )
            ),
            401: openapi.Response(description="인증 실패"),
            404: openapi.Response(description="세션을 찾을 수 없음")
        }
    )
    @clerk_auth_required
    def delete(self, request, session_id):
        session = get_object_or_404(Session, id=session_id, user=request.user, is_deleted=False)
        session.is_deleted = True
        session.save()

        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "세션이 삭제되었습니다.",
            "data": {"session_id": session.id, "title": session.title}
        }, status=status.HTTP_200_OK)
