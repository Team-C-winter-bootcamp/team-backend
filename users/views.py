import os
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.conf import settings
from svix.webhooks import Webhook, WebhookVerificationError

from .models import User
from .utils import verify_clerk_token

logger = logging.getLogger(__name__)


class TokenVerifyView(APIView):
    """
    Clerk Access Token 검증 API
    
    토큰의 다음 사항을 검증합니다:
    1. 위조되지 않았는지 (서명 검증)
    2. 만료되지 않았는지
    3. 이 서버에서 발급된 것인지 (발급자 확인)
    """
    
    @swagger_auto_schema(
        operation_summary="토큰 검증 API",
        operation_description="Clerk Access Token의 유효성을 검증합니다. 위조, 만료, 발급자를 확인합니다.\n\n**Swagger에서 테스트하기:**\n1. 실제 토큰: 프론트엔드에서 `await window.Clerk.session.getToken()` 실행하여 토큰 획득\n2. DEBUG 모드 테스트: `test_token_debug` 사용 (개발 환경 전용)\n3. Swagger UI의 'Authorize' 버튼 클릭 후 토큰 입력",
        tags=["사용자"],
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
            200: openapi.Response(
                description="토큰 검증 성공",
                examples={
                    "application/json": {
                        "status": "success",
                        "code": "COMMON_200",
                        "message": "토큰이 유효합니다.",
                        "data": {
                            "valid": True,
                            "user_id": "user_xxx",
                            "issuer": "https://xxx.clerk.accounts.dev"
                        }
                    }
                }
            ),
            401: openapi.Response(
                description="토큰 검증 실패",
                examples={
                    "application/json": {
                        "status": "error",
                        "code": "ERR_401",
                        "message": "토큰이 만료되었습니다.",
                        "data": {
                            "valid": False,
                            "error": "토큰이 만료되었습니다."
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="토큰 없음",
                examples={
                    "application/json": {
                        "status": "error",
                        "code": "ERR_400",
                        "message": "토큰이 제공되지 않았습니다."
                    }
                }
            )
        }
    )
    def post(self, request):
        """
        POST /users/token/verify
        
        Authorization 헤더에 Bearer 토큰을 포함하여 요청합니다.
        DEBUG 모드에서는 "test_token_debug"를 사용할 수 있습니다.
        """
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("Authorization", "")
        
        # Bearer 접두사가 없으면 자동으로 추가 (Swagger 호환성)
        if auth_header and not auth_header.startswith("Bearer "):
            auth_header = f"Bearer {auth_header}"
            logger.debug(f"Bearer 접두사 자동 추가: '{auth_header[:50]}...'")
        
        if not auth_header.startswith("Bearer "):
            return Response({
                "status": "error",
                "code": "ERR_400",
                "message": "토큰이 제공되지 않았습니다."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token = auth_header.split("Bearer ", 1)[1].strip()
        
        if not token:
            return Response({
                "status": "error",
                "code": "ERR_400",
                "message": "토큰이 제공되지 않았습니다."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 디버깅: DEBUG 모드와 토큰 값 확인
        logger.debug(f"DEBUG 모드: {settings.DEBUG}, 받은 토큰: '{token}', 토큰 길이: {len(token)}")
        
        # DEBUG 모드에서 테스트 토큰 허용 (공백 제거 후 비교)
        test_token = token.strip()
        if settings.DEBUG and test_token == "test_token_debug":
            logger.info("DEBUG 모드에서 테스트 토큰 사용됨")
            return Response({
                "status": "success",
                "code": "COMMON_200",
                "message": "토큰이 유효합니다. (DEBUG 모드 - 테스트 토큰)",
                "data": {
                    "valid": True,
                    "user_id": "test_debug_user",
                    "issuer": "debug-mode",
                    "expires_at": None
                }
            }, status=status.HTTP_200_OK)
        
        # DEBUG 모드가 아닌 경우 또는 테스트 토큰이 아닌 경우 실제 토큰 검증
        if not settings.DEBUG:
            logger.warning(f"DEBUG 모드가 비활성화되어 있습니다. 실제 Clerk 토큰이 필요합니다.")
        elif token != "test_token_debug":
            logger.debug(f"테스트 토큰이 아닙니다. 실제 Clerk 토큰 검증을 시도합니다.")
        
        # 토큰 검증
        is_valid, payload, error_message = verify_clerk_token(token)
        
        if not is_valid:
            # DEBUG 모드인 경우 더 자세한 에러 메시지 제공
            error_detail = error_message or "토큰 검증에 실패했습니다."
            if settings.DEBUG:
                error_detail += f" (DEBUG 모드: 테스트 토큰 'test_token_debug'를 사용하세요)"
            
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": error_detail,
                "data": {
                    "valid": False,
                    "error": error_message,
                    "debug_mode": settings.DEBUG,
                    "received_token_preview": token[:20] + "..." if len(token) > 20 else token
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # 검증 성공
        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "토큰이 유효합니다.",
            "data": {
                "valid": True,
                "user_id": payload.get("sub"),
                "issuer": payload.get("iss"),
                "expires_at": payload.get("exp")
            }
        }, status=status.HTTP_200_OK)


class UserMeView(APIView):
    """
    현재 로그인한 사용자 본인의 정보를 조회하는 API
    """
    
    @swagger_auto_schema(
        operation_summary="현재 사용자 정보 조회",
        operation_description="현재 로그인한 사용자 본인의 정보를 조회합니다.\n\n**Swagger에서 테스트하기:**\n1. 실제 토큰: 프론트엔드에서 `await window.Clerk.session.getToken()` 실행하여 토큰 획득\n2. DEBUG 모드 테스트: `test_token_debug` 사용 (개발 환경 전용)\n3. Swagger UI의 'Authorize' 버튼 클릭 후 토큰 입력",
        tags=["사용자"],
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
            200: openapi.Response(
                description="사용자 정보 조회 성공",
                examples={
                    "application/json": {
                        "status": "success",
                        "code": "COMMON_200",
                        "message": "사용자 정보 조회 성공",
                        "data": {
                            "user_id": 1,
                            "clerk_id": "user_xxx",
                            "email": "user@example.com",
                            "first_name": "홍",
                            "last_name": "길동"
                        }
                    }
                }
            ),
            401: openapi.Response(description="인증 실패")
        }
    )
    def get(self, request):
        """
        GET /users/me
        
        Authorization 헤더에 Bearer 토큰을 포함하여 요청합니다.
        DEBUG 모드에서는 "test_token_debug"를 사용할 수 있습니다.
        """
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("Authorization", "")
        
        # Bearer 접두사가 없으면 자동으로 추가 (Swagger 호환성)
        if auth_header and not auth_header.startswith("Bearer "):
            auth_header = f"Bearer {auth_header}"
            logger.debug(f"Bearer 접두사 자동 추가: '{auth_header[:50]}...'")
        
        if not auth_header.startswith("Bearer "):
            logger.warning(
                f"GET /api/users/me/ - 인증 실패: Authorization 헤더가 없습니다."
            )
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": "인증 토큰이 필요합니다."
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        token = auth_header.split("Bearer ", 1)[1].strip()
        
        # 디버깅: DEBUG 모드와 토큰 값 확인
        logger.debug(f"DEBUG 모드: {settings.DEBUG}, 받은 토큰: '{token}', 토큰 길이: {len(token)}")
        
        # DEBUG 모드에서 테스트 토큰 허용 (공백 제거 후 비교)
        test_token = token.strip()
        if settings.DEBUG and test_token == "test_token_debug":
            logger.info("DEBUG 모드에서 테스트 토큰 사용됨 (UserMeView)")
            # 테스트용 유저 자동 생성 또는 조회
            user, _ = User.objects.get_or_create(
                clerk_id="test_debug_user",
                defaults={
                    "email": "test@example.com",
                    "first_name": "테스트",
                    "last_name": "사용자"
                }
            )
            return Response({
                "status": "success",
                "code": "COMMON_200",
                "message": "사용자 정보 조회 성공 (DEBUG 모드 - 테스트 토큰)",
                "data": {
                    "user_id": user.id,
                    "clerk_id": user.clerk_id,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name
                }
            }, status=status.HTTP_200_OK)
        
        # DEBUG 모드가 아닌 경우 또는 테스트 토큰이 아닌 경우 실제 토큰 검증
        if not settings.DEBUG:
            logger.warning(f"DEBUG 모드가 비활성화되어 있습니다. 실제 Clerk 토큰이 필요합니다.")
        elif token != "test_token_debug":
            logger.debug(f"테스트 토큰이 아닙니다. 실제 Clerk 토큰 검증을 시도합니다.")
        
        # 토큰 검증
        is_valid, payload, error_message = verify_clerk_token(token)
        
        if not is_valid:
            # DEBUG 모드인 경우 더 자세한 에러 메시지 제공
            error_detail = error_message or "토큰 검증에 실패했습니다."
            if settings.DEBUG:
                error_detail += f" (DEBUG 모드: 테스트 토큰 'test_token_debug'를 사용하세요)"
            
            logger.warning(
                f"GET /api/users/me/ - 토큰 검증 실패: {error_message}. "
                f"토큰 미리보기: '{token[:20]}...' (길이: {len(token)}), DEBUG 모드: {settings.DEBUG}"
            )
            
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": error_detail,
                "data": {
                    "debug_mode": settings.DEBUG,
                    "received_token_preview": token[:20] + "..." if len(token) > 20 else token
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # clerk_id로 사용자 조회
        clerk_id = payload.get("sub")
        try:
            user = User.objects.get(clerk_id=clerk_id)
            logger.info(f"GET /api/users/me/ - 사용자 정보 조회 성공: clerk_id={clerk_id}, user_id={user.id}")
        except User.DoesNotExist:
            logger.warning(f"GET /api/users/me/ - 사용자를 찾을 수 없음: clerk_id={clerk_id}")
            return Response({
                "status": "error",
                "code": "ERR_404",
                "message": "사용자를 찾을 수 없습니다."
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            "status": "success",
            "code": "COMMON_200",
            "message": "사용자 정보 조회 성공",
            "data": {
                "user_id": user.id,
                "clerk_id": user.clerk_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name
            }
        }, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
class ClerkWebhookView(APIView):
    """
    Clerk Webhook 이벤트를 처리하는 뷰
    
    user.created, user.updated 이벤트를 처리하여 DB에 반영합니다.
    """
    
    @swagger_auto_schema(
        operation_summary="Clerk Webhook 수신",
        operation_description="Clerk에서 발생한 webhook 이벤트를 받아서 DB에 반영합니다. user.created, user.updated 이벤트를 처리합니다.\n\n**주의사항:**\n- 실제 Clerk webhook은 Svix 서명 검증이 필요합니다.\n- 테스트용으로는 Swagger의 예시 데이터를 사용할 수 없습니다.\n- 실제 webhook은 Clerk Dashboard에서 설정한 엔드포인트로만 전송됩니다.",
        tags=["사용자"],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            description="Clerk webhook 이벤트 데이터 (Svix로 래핑됨)",
            properties={
                "type": openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="이벤트 타입",
                    enum=["user.created", "user.updated"],
                    example="user.created"
                ),
                "data": openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    description="사용자 데이터",
                    properties={
                        "id": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="Clerk User ID",
                            example="user_2abc123def456"
                        ),
                        "email_addresses": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            description="이메일 주소 목록",
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "email_address": openapi.Schema(
                                        type=openapi.TYPE_STRING,
                                        example="user@example.com"
                                    )
                                }
                            ),
                            example=[{"email_address": "user@example.com"}]
                        ),
                        "first_name": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="이름",
                            example="홍"
                        ),
                        "last_name": openapi.Schema(
                            type=openapi.TYPE_STRING,
                            description="성",
                            example="길동"
                        )
                    },
                    required=["id"]
                )
            },
            required=["type", "data"],
            example={
                "type": "user.created",
                "data": {
                    "id": "user_2abc123def456",
                    "email_addresses": [
                        {
                            "email_address": "user@example.com"
                        }
                    ],
                    "first_name": "홍",
                    "last_name": "길동"
                }
            }
        ),
        responses={
            200: openapi.Response(
                description="Webhook 처리 성공",
                examples={
                    "application/json": {
                        "user.created 예시": {
                            "status": "success",
                            "code": "COMMON_200",
                            "message": "사용자가 생성되었습니다.",
                            "data": {
                                "user_id": 1,
                                "clerk_id": "user_2abc123def456",
                                "email": "user@example.com"
                            }
                        },
                        "user.updated 예시": {
                            "status": "success",
                            "code": "COMMON_200",
                            "message": "사용자 정보가 업데이트되었습니다.",
                            "data": {
                                "user_id": 1,
                                "clerk_id": "user_2abc123def456",
                                "email": "user@example.com"
                            }
                        }
                    }
                }
            ),
            401: openapi.Response(
                description="Webhook 검증 실패",
                examples={
                    "application/json": {
                        "status": "error",
                        "code": "ERR_401",
                        "message": "Webhook 검증 실패"
                    }
                }
            ),
            500: openapi.Response(
                description="서버 오류",
                examples={
                    "application/json": {
                        "status": "error",
                        "code": "ERR_500",
                        "message": "이벤트 처리 중 오류가 발생했습니다: [오류 내용]"
                    }
                }
            )
        }
    )
    def post(self, request):
        """
        POST /users/webhooks/clerk
        
        Clerk에서 발생한 이벤트를 받아서 DB에 반영합니다.
        """
        # Webhook 시크릿 키 가져오기
        webhook_secret = settings.CLERK_WEBHOOK_SECRET
        
        if not webhook_secret:
            logger.error("CLERK_WEBHOOK_SECRET이 설정되지 않았습니다.")
            return Response({
                "status": "error",
                "code": "ERR_500",
                "message": "서버 설정 오류"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        # Svix webhook 검증
        headers = {
            'svix-id': request.headers.get('svix-id', ''),
            'svix-timestamp': request.headers.get('svix-timestamp', ''),
            'svix-signature': request.headers.get('svix-signature', ''),
        }
        
        payload = request.body
        
        try:
            wh = Webhook(webhook_secret)
            evt = wh.verify(payload, headers)
        except WebhookVerificationError as e:
            logger.error(f"Webhook 검증 실패: {str(e)}")
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": "Webhook 검증 실패"
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # 이벤트 타입에 따라 처리
        event_type = evt.get("type")
        data = evt.get("data", {})
        
        if event_type == "user.created":
            return self._handle_user_created(data)
        elif event_type == "user.updated":
            return self._handle_user_updated(data)
        else:
            logger.info(f"처리하지 않는 이벤트 타입: {event_type}")
            return Response({
                "status": "success",
                "code": "COMMON_200",
                "message": f"이벤트 타입 {event_type}는 처리하지 않습니다."
            }, status=status.HTTP_200_OK)
    
    def _handle_user_created(self, data):
        """user.created 이벤트 처리"""
        try:
            clerk_id = data.get("id")
            email_addresses = data.get("email_addresses", [])
            email = email_addresses[0].get("email_address") if email_addresses else None
            
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            
            # 사용자 생성 또는 업데이트
            user, created = User.objects.update_or_create(
                clerk_id=clerk_id,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name
                }
            )
            
            action = "생성" if created else "업데이트"
            logger.info(f"사용자 {action}: clerk_id={clerk_id}, email={email}")
            
            return Response({
                "status": "success",
                "code": "COMMON_200",
                "message": f"사용자가 {action}되었습니다.",
                "data": {
                    "user_id": user.id,
                    "clerk_id": user.clerk_id,
                    "email": user.email
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"user.created 이벤트 처리 중 오류: {str(e)}")
            return Response({
                "status": "error",
                "code": "ERR_500",
                "message": f"이벤트 처리 중 오류가 발생했습니다: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _handle_user_updated(self, data):
        """user.updated 이벤트 처리"""
        try:
            clerk_id = data.get("id")
            email_addresses = data.get("email_addresses", [])
            email = email_addresses[0].get("email_address") if email_addresses else None
            
            first_name = data.get("first_name")
            last_name = data.get("last_name")
            
            # 사용자 업데이트
            user, created = User.objects.update_or_create(
                clerk_id=clerk_id,
                defaults={
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name
                }
            )
            
            logger.info(f"사용자 업데이트: clerk_id={clerk_id}, email={email}")
            
            return Response({
                "status": "success",
                "code": "COMMON_200",
                "message": "사용자 정보가 업데이트되었습니다.",
                "data": {
                    "user_id": user.id,
                    "clerk_id": user.clerk_id,
                    "email": user.email
                }
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"user.updated 이벤트 처리 중 오류: {str(e)}")
            return Response({
                "status": "error",
                "code": "ERR_500",
                "message": f"이벤트 처리 중 오류가 발생했습니다: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
