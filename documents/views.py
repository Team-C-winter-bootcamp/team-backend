from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .serializers import (
    DocumentGenerateRequestSerializer,
    DocumentGenerateResponseSerializer,
    DocumentGenerateFromSituationRequestSerializer,
    DocumentGenerateFromSituationResponseSerializer,
)
from .services import create_document, create_document_from_situation


class DocumentGenerateView(APIView):
    """
    문서 자동 생성 API

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
        operation_summary="문서 자동 생성 API",
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
