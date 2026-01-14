import json
import logging
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from svix.webhooks import Webhook, WebhookVerificationError

from users.models import User

# 로거 설정
logger = logging.getLogger(__name__)


def _get_primary_email(data):
    """Clerk 사용자 데이터에서 주 이메일 주소를 찾습니다."""
    primary_email_id = data.get("primary_email_address_id")
    for email_data in data.get("email_addresses", []):
        if email_data["id"] == primary_email_id:
            return email_data["email_address"]
    # 주 이메일을 찾지 못한 경우, 첫 번째 이메일을 반환 (Fallback)
    if data.get("email_addresses"):
        return data["email_addresses"][0]["email_address"]
    return None


@csrf_exempt
@transaction.atomic
def clerk_webhook(request):
    """
    Clerk에서 발생하는 사용자 관련 이벤트를 처리하는 웹훅입니다.
    Events: user.created, user.updated, user.deleted
    데이터베이스 변경 작업을 하나의 트랜잭션으로 처리합니다.
    """
    if request.method != "POST":
        return HttpResponse("잘못된 요청 메서드입니다.", status=405)

    # 헤더와 페이로드(본문) 가져오기
    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")
    payload = request.body

    # 필수 헤더 확인
    if not all([svix_id, svix_timestamp, svix_signature]):
        return HttpResponse("필수 헤더가 누락되었습니다.", status=400)

    # 웹훅 시크릿 키로 검증
    try:
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        evt = wh.verify(payload, {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        })
    except WebhookVerificationError:
        logger.warning("Clerk 웹훅 검증에 실패했습니다.")
        return HttpResponse("웹훅 검증에 실패했습니다.", status=401)

    # 이벤트 유형에 따라 처리
    event_type = evt["type"]
    data = evt["data"]
    

    try:
        if event_type == "user.created":
            email = _get_primary_email(data)
            if not email:
                logger.error(f"user.created 이벤트에 이메일이 없습니다. Clerk ID: {data['id']}")
                return HttpResponse("이메일 주소가 없어 사용자를 생성할 수 없습니다.", status=400)
            
            User.objects.create(
                clerk_id=data["id"],
                email=email,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                image_url=data.get("image_url"),
            )
        
        elif event_type == "user.updated":
            user = User.objects.select_for_update().get(clerk_id=data["id"])
            email = _get_primary_email(data)
            if email:
                user.email = email
            user.first_name = data.get("first_name")
            user.last_name = data.get("last_name")
            user.image_url = data.get("image_url")
            user.save()

        elif event_type == "user.deleted":
            clerk_id_to_delete = data.get("id")
            if clerk_id_to_delete:
                # is_active를 False로 설정하여 Soft Delete 처리
                User.objects.filter(clerk_id=clerk_id_to_delete).update(is_active=False)

    except User.DoesNotExist:
        logger.warning(f"업데이트/삭제하려는 사용자를 찾을 수 없습니다. Clerk ID: {data.get('id')}")
        return HttpResponse(f"User with clerk_id {data.get('id')} not found.", status=404)
    except Exception as e:
        logger.error(f"Clerk 웹훅 처리 중 에러 발생: {e}", exc_info=True)
        return HttpResponse("내부 서버 오류가 발생했습니다.", status=500)

    return HttpResponse("웹훅이 성공적으로 처리되었습니다.", status=200)