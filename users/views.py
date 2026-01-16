from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .utils import verify_clerk_token


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
        operation_description="Clerk Access Token의 유효성을 검증합니다. 위조, 만료, 발급자를 확인합니다.",
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
        """
        # Authorization 헤더에서 토큰 추출
        auth_header = request.headers.get("Authorization", "")
        
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
        
        # 토큰 검증
        is_valid, payload, error_message = verify_clerk_token(token)
        
        if not is_valid:
            return Response({
                "status": "error",
                "code": "ERR_401",
                "message": error_message or "토큰 검증에 실패했습니다.",
                "data": {
                    "valid": False,
                    "error": error_message
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
