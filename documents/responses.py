"""
API 응답 래퍼 유틸리티

모든 API 응답을 명세에 맞는 통일된 형식으로 반환합니다.
"""
from rest_framework.response import Response
from rest_framework import status


def success_response(data: dict, status_code: int = status.HTTP_200_OK) -> Response:
    """
    성공 응답을 생성합니다.

    Args:
        data: 응답 데이터
        status_code: HTTP 상태 코드 (기본값: 200)

    Returns:
        Response 객체

    Example:
        {
            "status": "success",
            "data": {
                "document_id": 501,
                "case_id": 123,
                "title": "...",
                "content": "..."
            }
        }
    """
    return Response(
        {
            "status": "success",
            "data": data
        },
        status=status_code
    )


def error_response(
    message: str,
    code: int = status.HTTP_400_BAD_REQUEST,
    additional_request: str = None
) -> Response:
    """
    에러 응답을 생성합니다.

    Args:
        message: 에러 메시지
        code: HTTP 상태 코드
        additional_request: 추가 요청 정보 (400 에러 시)

    Returns:
        Response 객체

    Example (400):
        {
            "status": "error",
            "code": 400,
            "message": "요청 형식이 올바르지 않습니다.",
            "error": {
                "additional_request": null
            }
        }

    Example (404):
        {
            "status": "error",
            "code": 404,
            "message": "요청한 리소스를 찾을 수 없습니다."
        }
    """
    response_data = {
        "status": "error",
        "code": code,
        "message": message
    }

    # 400 에러는 error.additional_request 필드 포함
    if code == status.HTTP_400_BAD_REQUEST:
        response_data["error"] = {
            "additional_request": additional_request
        }

    return Response(response_data, status=code)


def error_400(message: str = "요청 형식이 올바르지 않습니다.", additional_request: str = None) -> Response:
    """400 Bad Request 응답"""
    return error_response(message, status.HTTP_400_BAD_REQUEST, additional_request)


def error_404(message: str = "요청한 리소스를 찾을 수 없습니다.") -> Response:
    """404 Not Found 응답"""
    return error_response(message, status.HTTP_404_NOT_FOUND)


def error_500(message: str = "서버 내부 오류가 발생했습니다.") -> Response:
    """500 Internal Server Error 응답"""
    return error_response(message, status.HTTP_500_INTERNAL_SERVER_ERROR)
