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

