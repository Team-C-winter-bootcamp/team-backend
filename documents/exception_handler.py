"""
커스텀 예외 핸들러

개발 모드에서도 API 요청에 대해 HTML 디버그 페이지 대신 JSON 에러를 반환합니다.
"""
from rest_framework.views import exception_handler
from rest_framework import status


def custom_exception_handler(exc, context):
    """
    DRF 기본 예외 핸들러를 확장하여 통일된 에러 형식을 반환합니다.
    """
    # 기본 핸들러 호출
    response = exception_handler(exc, context)

    if response is not None:
        # DRF가 처리한 예외
        custom_response = {
            "status": "error",
            "code": response.status_code,
            "message": _get_error_message(response.status_code, response.data)
        }

        # 400 에러는 error.additional_request 추가
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            custom_response["error"] = {
                "additional_request": _format_detail(response.data)
            }

        response.data = custom_response

    return response


def _get_error_message(status_code: int, data) -> str:
    """상태 코드에 따른 기본 메시지 반환"""
    messages = {
        400: "요청 형식이 올바르지 않습니다.",
        401: "인증이 필요합니다.",
        403: "접근 권한이 없습니다.",
        404: "요청한 리소스를 찾을 수 없습니다.",
        405: "허용되지 않는 메소드입니다.",
        500: "서버 내부 오류가 발생했습니다.",
    }
    return messages.get(status_code, str(data))


def _format_detail(data) -> str:
    """에러 상세 정보를 문자열로 변환"""
    if isinstance(data, dict):
        if 'detail' in data:
            return str(data['detail'])
        return str(data)
    return str(data) if data else None
