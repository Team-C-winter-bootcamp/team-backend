"""
세션 기반 문서 작성 서비스

대화형으로 정보를 수집하여 법률 문서를 생성하는 비즈니스 로직을 제공합니다.
"""
import os
import json
from typing import Generator, Optional
from datetime import datetime

import google.genai as genai

from .models import Template, Document, DocumentSession, DocumentSessionMessage
from .services import get_active_template, validate_document


# 문서 유형별 한글 -> 영문 매핑
DOC_TYPE_MAPPING = {
    "내용증명서": "proof_of_contents",
    "내용증명": "proof_of_contents",
    "고소장": "criminal_complaint_fraud",
    "합의서": "settlement_agreement",
}

# 문서 유형별 필수 키와 설명 매핑
DOC_TYPE_REQUIRED_KEYS = {
    "proof_of_contents": {
        "sender_name": "발신인 이름",
        "sender_address": "발신인 주소",
        "sender_contact": "발신인 연락처",
        "receiver_name": "수신인 이름",
        "receiver_address": "수신인 주소",
        "transaction_date": "거래 일자",
        "transaction_details": "거래 내역",
        "claim_amount": "청구 금액",
        "payment_deadline": "지급 기한",
        "bank_account": "입금 계좌 정보",
        "written_date": "작성일",
    },
    "criminal_complaint_fraud": {
        "complainant_name": "고소인(피해자) 이름",
        "complainant_contact": "고소인 연락처",
        "suspect_name": "피고소인(가해자) 이름",
        "suspect_contact": "피고소인 연락처",
        "incident_datetime": "사건 발생 일시",
        "incident_place": "사건 발생 장소",
        "crime_facts": "범죄 사실",
        "damage_amount": "피해 금액",
        "complaint_reason": "고소 이유",
        "evidence_list": "증거 자료 목록",
        "attachments": "첨부 자료 목록",
        "request_purpose": "고소 목적",
        "written_date": "작성일",
    },
    "settlement_agreement": {
        "party_a_name": "갑(피해자) 이름",
        "party_a_contact": "갑 연락처",
        "party_a_address": "갑 주소",
        "party_b_name": "을(가해자) 이름",
        "party_b_contact": "을 연락처",
        "party_b_address": "을 주소",
        "incident_summary": "사건 개요",
        "settlement_amount": "합의 금액",
        "payment_method": "지급 방법",
        "payment_deadline": "지급 기한",
        "additional_terms": "추가 합의 조건",
        "written_date": "작성일",
    },
}


def get_gemini_client():
    """Gemini API 클라이언트를 반환합니다."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
    return genai.Client(api_key=api_key)


def get_gemini_model_name() -> str:
    """환경 변수에서 Gemini 모델명을 가져옵니다."""
    model_name = os.environ.get("GEMINI_MODEL")
    if not model_name:
        raise ValueError("GEMINI_MODEL 환경 변수가 설정되지 않았습니다.")
    return model_name.replace("models/", "").strip()


def create_session(case_id: int, document_type: str) -> DocumentSession:
    """
    새 문서 작성 세션을 생성합니다.

    Args:
        case_id: 케이스 ID
        document_type: 문서 유형 (한글 또는 영문)

    Returns:
        생성된 DocumentSession 객체

    Raises:
        ValueError: 템플릿을 찾을 수 없는 경우
    """
    # 문서 유형 매핑
    doc_type = DOC_TYPE_MAPPING.get(document_type, document_type)

    # 템플릿 조회
    template = get_active_template(doc_type)
    if not template:
        raise ValueError(f"템플릿을 찾을 수 없습니다: {document_type}")

    # 필수 키 설정
    required_keys = list(DOC_TYPE_REQUIRED_KEYS.get(doc_type, {}).keys())

    # 세션 생성
    session = DocumentSession.objects.create(
        case_id=case_id,
        document_type=document_type,
        template=template,
        status=DocumentSession.Status.WAITING,
        values={},
        required_keys=required_keys,
    )

    # 시스템 메시지 추가
    initial_message = f"안녕하세요! {document_type} 작성을 도와드리겠습니다. 필요한 정보를 순차적으로 여쭤볼게요."
    DocumentSessionMessage.objects.create(
        session=session,
        role=DocumentSessionMessage.Role.ASSISTANT,
        content=initial_message,
    )

    return session


def get_session(session_id: str) -> Optional[DocumentSession]:
    """
    세션을 조회합니다.

    Args:
        session_id: 세션 UUID

    Returns:
        DocumentSession 객체 또는 None
    """
    try:
        return DocumentSession.objects.get(id=session_id)
    except DocumentSession.DoesNotExist:
        return None


def extract_values_from_text(
    doc_type: str, text: str, existing_values: dict
) -> dict:
    """
    Gemini를 사용하여 텍스트에서 값을 추출합니다.

    Args:
        doc_type: 문서 유형 (영문)
        text: 사용자 입력 텍스트
        existing_values: 기존에 수집된 값들

    Returns:
        새로 추출된 값들 (기존 값과 병합되지 않음)
    """
    client = get_gemini_client()
    model_name = get_gemini_model_name()

    # 해당 문서 유형의 필수 키와 설명 가져오기
    key_descriptions = DOC_TYPE_REQUIRED_KEYS.get(doc_type, {})

    # 이미 수집된 키는 제외
    missing_keys = {k: v for k, v in key_descriptions.items() if k not in existing_values or not existing_values[k]}

    if not missing_keys:
        return {}

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""당신은 법률 문서 작성을 위한 정보 추출 전문가입니다.

아래 사용자 입력에서 법률 문서 작성에 필요한 정보를 추출해주세요.

## 사용자 입력
{text}

## 추출해야 할 정보
{json.dumps(missing_keys, ensure_ascii=False, indent=2)}

## 규칙
1. 텍스트에서 명시적으로 언급된 정보만 추출하세요.
2. 추측하지 마세요. 정보가 없으면 해당 키를 포함하지 마세요.
3. evidence_list, attachments, additional_terms 등 목록 필드는 배열 형태로 반환하세요.
4. written_date가 언급되지 않았으면 "{today}"를 사용하세요.
5. 금액은 숫자와 단위를 포함해서 작성하세요 (예: "300,000원")
6. 반드시 유효한 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.
7. 추출된 정보가 없으면 빈 객체 {{}}를 반환하세요.

## 출력 형식 (JSON)
추출된 키-값 쌍만 포함하세요.
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    # 응답 텍스트 추출
    if hasattr(response, 'text'):
        response_text = response.text.strip()
    elif hasattr(response, 'candidates') and len(response.candidates) > 0:
        response_text = response.candidates[0].content.parts[0].text.strip()
    else:
        return {}

    # JSON 코드 블록 제거
    if response_text.startswith('```json'):
        response_text = response_text[7:]
    elif response_text.startswith('```'):
        response_text = response_text[3:]
    if response_text.endswith('```'):
        response_text = response_text[:-3]

    try:
        extracted = json.loads(response_text.strip())
        # null이나 빈 문자열인 값은 제거
        return {k: v for k, v in extracted.items() if v is not None and v != ""}
    except json.JSONDecodeError:
        return {}


def get_missing_keys(required_keys: list, values: dict) -> list:
    """
    누락된 필수 키 목록을 반환합니다.

    Args:
        required_keys: 필수 키 목록
        values: 현재 수집된 값들

    Returns:
        누락된 키 목록
    """
    return [key for key in required_keys if key not in values or not values[key]]


def make_followup_question(doc_type: str, missing_keys: list, values_so_far: dict) -> str:
    """
    Gemini를 사용하여 후속 질문을 생성합니다.

    Args:
        doc_type: 문서 유형 (영문)
        missing_keys: 누락된 키 목록
        values_so_far: 현재까지 수집된 값들

    Returns:
        후속 질문 문자열
    """
    if not missing_keys:
        return "모든 정보가 수집되었습니다. 문서를 생성할까요?"

    client = get_gemini_client()
    model_name = get_gemini_model_name()

    # 해당 문서 유형의 키 설명 가져오기
    key_descriptions = DOC_TYPE_REQUIRED_KEYS.get(doc_type, {})

    # 누락된 키의 설명만 추출
    missing_descriptions = {k: key_descriptions.get(k, k) for k in missing_keys}

    prompt = f"""당신은 친절한 법률 문서 작성 어시스턴트입니다.

문서 작성을 위해 아직 수집되지 않은 정보가 있습니다. 사용자에게 자연스럽게 질문해주세요.

## 수집된 정보
{json.dumps(values_so_far, ensure_ascii=False, indent=2) if values_so_far else "아직 수집된 정보가 없습니다."}

## 아직 필요한 정보
{json.dumps(missing_descriptions, ensure_ascii=False, indent=2)}

## 규칙
1. 한 번에 1~3개의 관련 정보만 질문하세요.
2. 자연스럽고 친절한 어투를 사용하세요.
3. 질문만 반환하세요. 다른 설명은 포함하지 마세요.
4. 예시를 포함하면 사용자가 이해하기 쉽습니다.
"""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    if hasattr(response, 'text'):
        return response.text.strip()
    elif hasattr(response, 'candidates') and len(response.candidates) > 0:
        return response.candidates[0].content.parts[0].text.strip()
    else:
        # 기본 질문 생성
        first_missing = list(missing_descriptions.values())[:3]
        return f"다음 정보를 알려주세요: {', '.join(first_missing)}"


def process_user_message(session: DocumentSession, content: str) -> Generator[dict, None, None]:
    """
    사용자 메시지를 처리하고 SSE 이벤트를 생성합니다.

    Args:
        session: DocumentSession 객체
        content: 사용자 메시지 내용

    Yields:
        SSE 이벤트 딕셔너리: {"event": str, "data": dict}
    """
    # 사용자 메시지 저장
    user_message = DocumentSessionMessage.objects.create(
        session=session,
        role=DocumentSessionMessage.Role.USER,
        content=content,
    )

    # 문서 유형 매핑
    doc_type = DOC_TYPE_MAPPING.get(session.document_type, session.document_type)

    # 1. 값 추출 중 상태
    session.status = DocumentSession.Status.EXTRACTING
    session.save(update_fields=['status', 'updated_at'])

    yield {"event": "status", "data": {"status": "extracting"}}

    try:
        # 2. 텍스트에서 값 추출
        extracted = extract_values_from_text(doc_type, content, session.values)

        # 추출된 값 이벤트 발생
        for key, value in extracted.items():
            yield {"event": "extracted", "data": {"key": key, "value": value}}

        # 메시지에 추출된 값 저장
        user_message.extracted_values = extracted
        user_message.save(update_fields=['extracted_values'])

        # 세션 값 병합
        session.values.update(extracted)
        session.save(update_fields=['values', 'updated_at'])

        # 3. 누락된 키 확인
        missing_keys = get_missing_keys(session.required_keys, session.values)

        if missing_keys:
            # 아직 수집할 정보가 있음 - 후속 질문 생성
            session.status = DocumentSession.Status.QUESTIONING
            session.save(update_fields=['status', 'updated_at'])

            yield {"event": "status", "data": {"status": "questioning"}}

            question = make_followup_question(doc_type, missing_keys, session.values)

            # 어시스턴트 메시지 저장
            DocumentSessionMessage.objects.create(
                session=session,
                role=DocumentSessionMessage.Role.ASSISTANT,
                content=question,
            )

            yield {"event": "question", "data": {"message": question}}

        else:
            # 모든 정보 수집 완료 - 문서 생성
            yield from generate_document_stream(session)

    except Exception as e:
        session.status = DocumentSession.Status.FAILED
        session.save(update_fields=['status', 'updated_at'])

        yield {
            "event": "error",
            "data": {"code": "PROCESSING_ERROR", "message": str(e)}
        }


def generate_document_stream(session: DocumentSession) -> Generator[dict, None, None]:
    """
    문서를 생성하고 SSE 이벤트를 발생시킵니다.

    Args:
        session: DocumentSession 객체

    Yields:
        SSE 이벤트 딕셔너리: {"event": str, "data": dict}
    """
    from .services import generate_document_with_gemini

    session.status = DocumentSession.Status.GENERATING
    session.save(update_fields=['status', 'updated_at'])

    yield {"event": "status", "data": {"status": "generating"}}

    try:
        # 문서 생성
        generated_content = generate_document_with_gemini(session.template, session.values)

        # 초안 저장
        session.last_draft = generated_content
        session.save(update_fields=['last_draft', 'updated_at'])

        yield {"event": "draft", "data": {"content": generated_content}}

        # 검증
        validation_result = validate_document(
            template_content=session.template.content_md,
            generated_content=generated_content
        )

        # Document 저장
        document = Document.objects.create(
            template=session.template,
            case_id=str(session.case_id),
            content_md=generated_content,
            validation_result=validation_result,
            input_values=session.values,
        )

        # 세션 업데이트
        session.document = document
        session.status = DocumentSession.Status.COMPLETED
        session.save(update_fields=['document', 'status', 'updated_at'])

        yield {
            "event": "done",
            "data": {
                "document_id": document.id,
                "session_id": str(session.id),
            }
        }

    except Exception as e:
        session.status = DocumentSession.Status.FAILED
        session.save(update_fields=['status', 'updated_at'])

        yield {
            "event": "error",
            "data": {"code": "GENERATION_ERROR", "message": str(e)}
        }
