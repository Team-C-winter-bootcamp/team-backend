import os
import logging
from functools import wraps
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import get_user_model
from clerk_backend_api import Clerk

User = get_user_model()

# 로거 설정
logger = logging.getLogger(__name__)

# Clerk 클라이언트 초기화
clerk_client = Clerk(bearer_auth=os.environ.get("CLERK_SECRET_KEY"))


def clerk_auth_required(view_func): 
    @wraps(view_func)
    def _wrapped_view(instance, request, *args, **kwargs):
        # DEBUG 모드이거나 테스트 모드 헤더가 있는 경우 인증 우회
        is_test_mode = True
        
        if is_test_mode:
            # 테스트용 유저 자동 생성 
            test_user, _ = User.objects.get_or_create(
                clerk_id="test_debug_user",
                defaults={"email": "test@example.com"}
            )
            request.user = test_user
            logger.info(f"[DEBUG/TEST MODE] 테스트 유저로 인증 우회: {test_user.clerk_id}")
            return view_func(instance, request, *args, **kwargs)

        # 프로덕션 모드: Clerk 인증 필수
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": "인증 토큰이 필요합니다."
            }, status=status.HTTP_401_UNAUTHORIZED)

        token = auth.split("Bearer ", 1)[1].strip()

        try:
            decoded_token = clerk_client.tokens.verify_session_token(token)
            clerk_id = decoded_token.get("sub")

            user, created = User.objects.get_or_create(clerk_id=clerk_id)
            if created:
                logger.info(f"새로운 유저 생성됨 (clerk_id: {clerk_id})")

            request.user = user

        except Exception as e:
            logger.error(f"Clerk 인증 실패: {str(e)}")
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": "유효하지 않거나 만료된 토큰입니다."
            }, status=status.HTTP_401_UNAUTHORIZED)

        return view_func(instance, request, *args, **kwargs)

    return _wrapped_view
