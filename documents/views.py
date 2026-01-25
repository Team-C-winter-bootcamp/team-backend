from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.negotiation import BaseContentNegotiation
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import json


class IgnoreClientContentNegotiation(BaseContentNegotiation):
    """
    Accept 헤더를 무시하고 항상 JSON 렌더러를 사용합니다.
    text/event-stream 등 비표준 Accept 헤더를 허용하기 위함.
    """
    def select_parser(self, request, parsers):
        return parsers[0]

    def select_renderer(self, request, renderers, format_suffix=None):
        return (renderers[0], renderers[0].media_type)

from .serializers import (
    DocumentGenerateRequestSerializer,
    DocumentGenerateResponseSerializer,
    DocumentGenerateFromSituationRequestSerializer,
    DocumentGenerateFromSituationResponseSerializer,
    CaseDocumentCreateRequestSerializer,
    CaseDocumentSuccessResponseSerializer,
    CaseDocumentErrorResponseSerializer,
    DocumentSessionCreateRequestSerializer,
    DocumentSessionMessageRequestSerializer,
    DocumentSessionResponseSerializer,
    DocumentDetailSerializer,
)
from .services import create_document, create_document_from_situation
from .session_services import (
    create_session,
    get_session,
    process_user_message,
    generate_document_stream,
    get_missing_keys,
)
from .responses import success_response, error_400, error_404, error_500


class DocumentGenerateView(APIView):
    """
    [DEPRECATED] 문서 자동 생성 API

    ⚠️ 이 API는 deprecated 되었습니다.
    새로운 API: POST /api/cases/{case_id}/documents 를 사용하세요.

    템플릿과 변수 값을 기반으로 Gemini API를 사용하여
    고소장 등의 법률 문서를 자동 생성합니다.
    """

    @swagger_auto_schema(
        request_body=DocumentGenerateRequestSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="문서 생성 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'pass': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='검증 통과 여부'),
                        'content_md': openapi.Schema(type=openapi.TYPE_STRING, description='생성된 Markdown 문서'),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='오류 목록'
                        ),
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: "잘못된 요청 형식입니다.",
            status.HTTP_404_NOT_FOUND: "템플릿을 찾을 수 없습니다.",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "서버 내부 오류가 발생했습니다."
        },
        operation_summary="[DEPRECATED] 문서 자동 생성 API",
        tags=["documents"],
        deprecated=True,
        operation_description="""
        사기 고소장 등 법률 문서를 자동 생성합니다.

        **doc_type 예시:**
        - `criminal_complaint_fraud`: 사기 고소장

        **values 예시:**
        ```json
        {
            "complainant_name": "홍길동",
            "complainant_contact": "010-1234-5678",
            "suspect_name": "김철수",
            "suspect_contact": "알 수 없음",
            "incident_datetime": "2025-12-10 14:30",
            "incident_place": "중고거래 채팅 및 계좌이체",
            "crime_facts": "중고거래로 30만원을 송금했으나 물품 미발송 및 연락두절",
            "damage_amount": "300,000",
            "complaint_reason": "계획적 기망에 의한 재산상 피해",
            "evidence_list": ["계좌이체 내역", "채팅 캡처", "판매글 캡처"],
            "attachments": ["신분증 사본"],
            "request_purpose": "피고소인 처벌 및 피해금 환급",
            "written_date": "2026-01-22"
        }
        ```

        **검증 규칙:**
        - {{...}} 플레이스홀더가 남아있으면 FAIL (UNRESOLVED_PLACEHOLDER)
        - 템플릿 헤더가 누락되면 FAIL (MISSING_SECTION)
        - 템플릿에 없는 헤더가 추가되면 FAIL (EXTRA_SECTION)
        """
    )
    def post(self, request, *args, **kwargs):
        serializer = DocumentGenerateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        doc_type = validated_data['doc_type']
        values = validated_data['values']
        case_id = validated_data.get('case_id')

        result = create_document(
            doc_type=doc_type,
            values=values,
            case_id=case_id
        )

        # 템플릿을 찾을 수 없는 경우
        if "TEMPLATE_NOT_FOUND" in result.get("errors", []):
            return Response(
                {
                    "pass": False,
                    "content_md": "",
                    "errors": ["TEMPLATE_NOT_FOUND"]
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # 설정 오류나 생성 오류인 경우
        if any(err.startswith(("CONFIG_ERROR", "GENERATION_ERROR")) for err in result.get("errors", [])):
            return Response(
                result,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result, status=status.HTTP_201_CREATED)


class DocumentGenerateFromSituationView(APIView):
    """
    상황 기반 문서 자동 생성 API

    사용자가 자유롭게 작성한 상황 설명을 분석하여
    필요한 정보를 추출하고 법률 문서를 자동 생성합니다.
    """

    @swagger_auto_schema(
        request_body=DocumentGenerateFromSituationRequestSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="문서 생성 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'pass': openapi.Schema(type=openapi.TYPE_BOOLEAN, description='검증 통과 여부'),
                        'content_md': openapi.Schema(type=openapi.TYPE_STRING, description='생성된 Markdown 문서'),
                        'errors': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_STRING),
                            description='오류 목록'
                        ),
                        'extracted_values': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            description='상황에서 추출된 값들'
                        ),
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: "잘못된 요청 형식입니다.",
            status.HTTP_404_NOT_FOUND: "템플릿을 찾을 수 없습니다.",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "서버 내부 오류가 발생했습니다."
        },
        operation_summary="상황 기반 문서 자동 생성 API",
        tags=["documents"],
        operation_description="""
        사용자가 자유롭게 작성한 상황 설명을 AI가 분석하여 고소장을 자동 생성합니다.

        **요청 예시:**
        ```json
        {
            "doc_type": "criminal_complaint_fraud",
            "situation": "저는 홍길동이고 연락처는 010-1234-5678입니다. 12월 10일에 중고나라에서 김철수라는 사람한테 에어팟 프로를 30만원에 산다고 계좌이체했는데, 돈 받고 나서 물건도 안보내고 연락이 두절됐어요. 카카오톡 채팅 내역이랑 계좌이체 내역 캡처해뒀습니다. 사기꾼 처벌받게 해주세요."
        }
        ```

        **응답:**
        - `pass`: 검증 통과 여부
        - `content_md`: 생성된 고소장 (Markdown)
        - `errors`: 오류 목록
        - `extracted_values`: AI가 상황에서 추출한 정보들

        **AI가 자동으로 추출하는 정보:**
        - 고소인/피고소인 인적사항
        - 사건 일시/장소
        - 범죄 사실
        - 피해 금액
        - 증거 자료 등
        """
    )
    def post(self, request, *args, **kwargs):
        serializer = DocumentGenerateFromSituationRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        validated_data = serializer.validated_data
        doc_type = validated_data['doc_type']
        situation = validated_data['situation']
        case_id = validated_data.get('case_id')

        result = create_document_from_situation(
            doc_type=doc_type,
            situation_text=situation,
            case_id=case_id
        )

        # 템플릿을 찾을 수 없는 경우
        if "TEMPLATE_NOT_FOUND" in result.get("errors", []):
            return Response(
                {
                    "pass": False,
                    "content_md": "",
                    "errors": ["TEMPLATE_NOT_FOUND"],
                    "extracted_values": {}
                },
                status=status.HTTP_404_NOT_FOUND
            )

        # 설정 오류나 추출/생성 오류인 경우
        if any(err.startswith(("CONFIG_ERROR", "EXTRACTION_ERROR", "GENERATION_ERROR")) for err in result.get("errors", [])):
            return Response(
                result,
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(result, status=status.HTTP_201_CREATED)


# ============================================================
# 신규 API: POST /cases/{case_id}/documents
# ============================================================

class CaseDocumentCreateView(APIView):
    """
    케이스 기반 문서 생성 API

    특정 케이스에 연결된 문서를 생성합니다.
    Accept: text/event-stream 헤더를 허용하지만,
    현재는 SSE 스트리밍 없이 일반 JSON 응답을 반환합니다.
    """
    # Accept: text/event-stream 헤더도 허용하기 위해 content negotiation 무시
    renderer_classes = [JSONRenderer]
    content_negotiation_class = IgnoreClientContentNegotiation

    @swagger_auto_schema(
        request_body=CaseDocumentCreateRequestSerializer,
        responses={
            status.HTTP_200_OK: CaseDocumentSuccessResponseSerializer,
            status.HTTP_400_BAD_REQUEST: CaseDocumentErrorResponseSerializer,
            status.HTTP_404_NOT_FOUND: CaseDocumentErrorResponseSerializer,
            status.HTTP_500_INTERNAL_SERVER_ERROR: CaseDocumentErrorResponseSerializer,
        },
        operation_summary="케이스 기반 문서 생성 API",
        tags=["cases"],
        operation_description="""
        특정 케이스에 연결된 법률 문서를 생성합니다.

        **요청 예시:**
        ```json
        {
            "document_type": "내용증명",
            "case_id": 123
        }
        ```

        **성공 응답 (200 OK):**
        ```json
        {
            "status": "success",
            "data": {
                "document_id": 501,
                "case_id": 123,
                "title": "금전거래 관련 고소장",
                "content": "# 고소장\\n\\n## 1. 고소인\\n..."
            }
        }
        ```

        **에러 응답 (400 Bad Request):**
        ```json
        {
            "status": "error",
            "code": 400,
            "message": "요청 형식이 올바르지 않습니다.",
            "error": {
                "additional_request": null
            }
        }
        ```

        **참고:**
        - path parameter의 case_id와 body의 case_id가 일치해야 합니다.
        - document_type은 필수 필드입니다.
        - Accept: text/event-stream 헤더는 허용되지만, 현재 SSE 스트리밍은 미구현입니다.
        """
    )
    def post(self, request, case_id, *args, **kwargs):
        # 1. 요청 검증
        serializer = CaseDocumentCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=str(serializer.errors)
            )

        validated_data = serializer.validated_data
        body_case_id = validated_data['case_id']
        document_type = validated_data['document_type']

        # 2. path param과 body의 case_id 일치 여부 확인
        if int(case_id) != int(body_case_id):
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=f"path case_id({case_id})와 body case_id({body_case_id})가 일치하지 않습니다."
            )

        # 3. document_type을 doc_type으로 매핑 (기존 템플릿 조회 호환)
        # 한글 document_type을 영문 doc_type으로 변환하는 매핑
        doc_type_mapping = {
            "내용증명서": "proof_of_contents",
            "고소장": "criminal_complaint_fraud",
            "합의서": "settlement_agreement",
            # 추가 매핑은 필요에 따라 확장
        }
        doc_type = doc_type_mapping.get(document_type, document_type)

        # 4. 문서 생성 (기존 서비스 재사용)
        try:
            from .services import get_active_template, generate_document_with_gemini, validate_document
            from .models import Document

            # 템플릿 조회
            template = get_active_template(doc_type)
            if not template:
                return error_404(message="요청한 리소스를 찾을 수 없습니다.")

            # 문서 생성 (요청 body의 values 사용)
            values = validated_data.get("values", {})
            generated_content = generate_document_with_gemini(template, values)

            # 검증
            validation_result = validate_document(
                template_content=template.content_md,
                generated_content=generated_content
            )

            # DB 저장
            document = Document.objects.create(
                template=template,
                case_id=str(case_id),
                content_md=generated_content,
                validation_result=validation_result,
                input_values=values
            )

            # 5. 성공 응답
            return success_response({
                "document_id": document.id,
                "case_id": int(case_id),
                "title": template.name,
                "content": generated_content
            })

        except ValueError as e:
            return error_500(message="서버 내부 오류가 발생했습니다.")
        except Exception as e:
            return error_500(message="서버 내부 오류가 발생했습니다.")


# ============================================================
# 세션 기반 문서 작성 API
# ============================================================

def sse_event(event: str, data: dict) -> str:
    """SSE 이벤트 문자열을 생성합니다."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class DocumentSessionCreateView(APIView):
    """
    문서 작성 세션 생성 API
    POST /api/cases/{case_id}/document-sessions/
    """

    @swagger_auto_schema(
        request_body=DocumentSessionCreateRequestSerializer,
        responses={
            status.HTTP_201_CREATED: openapi.Response(
                description="세션 생성 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, default='success'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'session_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                                'case_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'document_type': openapi.Schema(type=openapi.TYPE_STRING),
                                'status': openapi.Schema(type=openapi.TYPE_STRING),
                                'message': openapi.Schema(type=openapi.TYPE_STRING),
                            }
                        ),
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: CaseDocumentErrorResponseSerializer,
            status.HTTP_404_NOT_FOUND: CaseDocumentErrorResponseSerializer,
        },
        operation_summary="문서 작성 세션 생성",
        tags=["document-sessions"],
        operation_description="""
        새로운 문서 작성 세션을 생성합니다.

        **요청 예시:**
        ```json
        {
            "document_type": "내용증명서"
        }
        ```

        **document_type 옵션:**
        - `내용증명서` / `내용증명` / `proof_of_contents`
        - `고소장` / `criminal_complaint_fraud`
        - `합의서` / `settlement_agreement`
        """
    )
    def post(self, request, case_id, *args, **kwargs):
        serializer = DocumentSessionCreateRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=str(serializer.errors)
            )

        document_type = serializer.validated_data['document_type']

        try:
            session = create_session(case_id=int(case_id), document_type=document_type)

            # 첫 번째 메시지 가져오기
            first_message = session.messages.first()

            return success_response(
                {
                    "session_id": str(session.id),
                    "case_id": session.case_id,
                    "document_type": session.document_type,
                    "status": session.status,
                    "message": first_message.content if first_message else "",
                },
                status_code=status.HTTP_201_CREATED
            )

        except ValueError as e:
            return error_404(message=str(e))
        except Exception as e:
            return error_500(message="서버 내부 오류가 발생했습니다.")


class DocumentSessionDetailView(APIView):
    """
    세션 상태 조회 API
    GET /api/cases/{case_id}/document-sessions/{session_id}/
    """

    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: DocumentSessionResponseSerializer,
            status.HTTP_404_NOT_FOUND: CaseDocumentErrorResponseSerializer,
        },
        operation_summary="세션 상태 조회",
        tags=["document-sessions"],
        operation_description="""
        세션의 현재 상태와 수집된 정보를 조회합니다.

        **응답 필드:**
        - `session_id`: 세션 UUID
        - `status`: 세션 상태 (waiting, extracting, questioning, generating, completed, failed)
        - `required_keys`: 필수 키 목록
        - `collected_keys`: 수집 완료된 키 목록
        - `missing_keys`: 누락된 키 목록
        - `values`: 수집된 값들
        - `messages`: 메시지 목록
        - `document_id`: 생성된 문서 ID (완료 시)
        """
    )
    def get(self, request, case_id, session_id, *args, **kwargs):
        session = get_session(session_id)
        if not session:
            return error_404(message="세션을 찾을 수 없습니다.")

        if session.case_id != int(case_id):
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=f"세션의 case_id가 일치하지 않습니다."
            )

        # 수집된 키, 누락된 키 계산
        collected_keys = [k for k in session.required_keys if k in session.values and session.values[k]]
        missing_keys = get_missing_keys(session.required_keys, session.values)

        # 메시지 목록
        messages = [
            {
                "role": msg.role,
                "content": msg.content,
                "extracted_values": msg.extracted_values,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in session.messages.all()
        ]

        return success_response({
            "session_id": str(session.id),
            "case_id": session.case_id,
            "document_type": session.document_type,
            "status": session.status,
            "required_keys": session.required_keys,
            "collected_keys": collected_keys,
            "missing_keys": missing_keys,
            "values": session.values,
            "messages": messages,
            "document_id": session.document.id if session.document else None,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
        })


class DocumentSessionMessageView(APIView):
    """
    세션 메시지 전송 API
    POST /api/cases/{case_id}/document-sessions/{session_id}/messages/
    """
    renderer_classes = [JSONRenderer]
    content_negotiation_class = IgnoreClientContentNegotiation

    @swagger_auto_schema(
        request_body=DocumentSessionMessageRequestSerializer,
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="메시지 처리 완료 (JSON 응답 또는 SSE 스트림)",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT),
                    }
                )
            ),
            status.HTTP_400_BAD_REQUEST: CaseDocumentErrorResponseSerializer,
            status.HTTP_404_NOT_FOUND: CaseDocumentErrorResponseSerializer,
        },
        operation_summary="세션 메시지 전송",
        tags=["document-sessions"],
        operation_description="""
        세션에 메시지를 전송합니다.

        **요청 예시:**
        ```json
        {
            "content": "저는 홍길동이고, 주소는 서울시 강남구입니다."
        }
        ```

        **SSE 스트리밍:**
        - `Accept: text/event-stream` 헤더를 포함하면 SSE 스트림으로 응답합니다.
        - 헤더가 없으면 일반 JSON 응답을 반환합니다.

        **SSE 이벤트:**
        - `status`: 상태 변경 (extracting, questioning, generating)
        - `extracted`: 값 추출 완료 (key, value)
        - `question`: 후속 질문
        - `draft`: 문서 초안 생성 완료
        - `done`: 문서 생성 완료 (document_id, session_id)
        - `error`: 오류 발생 (code, message)
        """
    )
    def post(self, request, case_id, session_id, *args, **kwargs):
        session = get_session(session_id)
        if not session:
            return error_404(message="세션을 찾을 수 없습니다.")

        if session.case_id != int(case_id):
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=f"세션의 case_id가 일치하지 않습니다."
            )

        if session.status == 'completed':
            return error_400(
                message="이미 완료된 세션입니다.",
                additional_request="새 세션을 생성해주세요."
            )

        if session.status == 'failed':
            return error_400(
                message="실패한 세션입니다.",
                additional_request="새 세션을 생성해주세요."
            )

        serializer = DocumentSessionMessageRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=str(serializer.errors)
            )

        content = serializer.validated_data['content']

        # SSE 스트리밍 여부 확인
        accept_header = request.headers.get('Accept', '')
        use_sse = 'text/event-stream' in accept_header

        if use_sse:
            # SSE 스트리밍 응답
            def event_stream():
                for event in process_user_message(session, content):
                    yield sse_event(event['event'], event['data'])

            return StreamingHttpResponse(
                event_stream(),
                content_type='text/event-stream',
            )
        else:
            # JSON 응답 (모든 이벤트를 수집하여 반환)
            events = list(process_user_message(session, content))
            last_event = events[-1] if events else {}

            # 세션 새로고침
            session.refresh_from_db()

            # 수집된 키 계산
            collected_keys = [k for k in session.required_keys if k in session.values and session.values[k]]
            missing_keys = get_missing_keys(session.required_keys, session.values)

            response_data = {
                "session_id": str(session.id),
                "status": session.status,
                "collected_keys": collected_keys,
                "missing_keys": missing_keys,
                "values": session.values,
                "events": events,
            }

            if session.document:
                response_data["document_id"] = session.document.id

            return success_response(response_data)


class DocumentSessionStreamView(APIView):
    """
    SSE 스트림 재접속 API
    GET /api/cases/{case_id}/document-sessions/{session_id}/stream/
    """

    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="SSE 스트림",
            ),
            status.HTTP_404_NOT_FOUND: CaseDocumentErrorResponseSerializer,
        },
        operation_summary="SSE 스트림 (재접속용)",
        tags=["document-sessions"],
        operation_description="""
        세션의 현재 상태를 SSE 스트림으로 반환합니다.
        재접속 시 사용합니다.
        """
    )
    def get(self, request, case_id, session_id, *args, **kwargs):
        session = get_session(session_id)
        if not session:
            return error_404(message="세션을 찾을 수 없습니다.")

        if session.case_id != int(case_id):
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=f"세션의 case_id가 일치하지 않습니다."
            )

        def event_stream():
            # 현재 상태 전송
            yield sse_event("status", {"status": session.status})

            # 수집된 값 전송
            for key, value in session.values.items():
                yield sse_event("extracted", {"key": key, "value": value})

            # 마지막 초안이 있으면 전송
            if session.last_draft:
                yield sse_event("draft", {"content": session.last_draft})

            # 완료 또는 실패 상태면 해당 이벤트 전송
            if session.status == 'completed' and session.document:
                yield sse_event("done", {
                    "document_id": session.document.id,
                    "session_id": str(session.id),
                })
            elif session.status == 'failed':
                yield sse_event("error", {
                    "code": "SESSION_FAILED",
                    "message": "세션이 실패 상태입니다.",
                })

        return StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream',
        )


class CaseDocumentDetailView(APIView):
    """
    문서 상세 조회 API
    GET /api/cases/{case_id}/documents/{document_id}/
    """

    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: openapi.Response(
                description="문서 조회 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'status': openapi.Schema(type=openapi.TYPE_STRING, default='success'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'document_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'case_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'title': openapi.Schema(type=openapi.TYPE_STRING),
                                'content': openapi.Schema(type=openapi.TYPE_STRING),
                                'validation_result': openapi.Schema(type=openapi.TYPE_OBJECT),
                                'created_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                            }
                        ),
                    }
                )
            ),
            status.HTTP_404_NOT_FOUND: CaseDocumentErrorResponseSerializer,
        },
        operation_summary="문서 상세 조회",
        tags=["cases"],
        operation_description="""
        생성된 문서를 조회합니다.

        **응답 필드:**
        - `document_id`: 문서 ID
        - `case_id`: 케이스 ID
        - `title`: 문서 제목 (템플릿명)
        - `content`: 문서 내용 (Markdown)
        - `validation_result`: 검증 결과
        - `created_at`: 생성 시간
        """
    )
    def get(self, request, case_id, document_id, *args, **kwargs):
        from .models import Document

        try:
            document = Document.objects.select_related('template').get(id=document_id)
        except Document.DoesNotExist:
            return error_404(message="문서를 찾을 수 없습니다.")

        # case_id 일치 확인
        if document.case_id and str(document.case_id) != str(case_id):
            return error_400(
                message="요청 형식이 올바르지 않습니다.",
                additional_request=f"문서의 case_id가 일치하지 않습니다."
            )

        return success_response({
            "document_id": document.id,
            "case_id": int(case_id),
            "title": document.template.name,
            "content": document.content_md,
            "validation_result": document.validation_result,
            "created_at": document.created_at.isoformat(),
        })
