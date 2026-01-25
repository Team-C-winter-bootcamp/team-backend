from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from cases.models import Case
from .models import Template, Document
from .service import *
from .serializers import *


class DocumentView(APIView):

    @swagger_auto_schema(
        operation_summary="법률 문서 AI 생성 및 저장",
        operation_description=(
                "특정 사건(case_id)과 판례를 기반으로 AI가 문서를 생성하고 저장합니다. "
                "생성된 문서의 인적 사항 등 불확실한 정보는 {{변수}} 형태로 유지됩니다."
        ),
        query_serializer=None,
        request_body=DocumentCreateRequestSerializer,
        responses={201: DocumentResponseSerializer()},
    )
    def post(self, request, *args, **kwargs):
        # 1. 데이터 검증
        serializer = DocumentCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc_type = serializer.validated_data.get('type')
        case_id = serializer.validated_data.get('case_id')
        precedent = serializer.validated_data.get('precedent')

        # 2. Case 및 Template 직접 조회 (예외 처리)
        try:
            case_obj = Case.objects.get(id=case_id, is_deleted=False)
            template = Template.objects.get(type=doc_type, is_deleted=False)
        except Case.DoesNotExist:
            return Response({"error": f"ID {case_id}에 해당하는 사건 정보를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Template.DoesNotExist:
            return Response({"error": f"'{doc_type}' 타입의 기본 템플릿이 DB에 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # 3. AI 서비스 호출을 위한 데이터 구성
        case_data_string = (
            f"대상: {case_obj.who}\n"
            f"일시: {case_obj.when}\n"
            f"사건내용: {case_obj.what}\n"
            f"희망결과: {case_obj.want}\n"
            f"상세설명: {case_obj.detail}"
        )

        try:
            # AI 서비스 호출 (프롬프트 지침에 따라 순수 본문만 생성)
            generated_content = generate_legal_document(
                case_data=case_data_string,
                precedent_data=precedent,
                template_content=template.content
            )
        except Exception as e:
            return Response({"error": f"AI 문서 생성 실패: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 4. Document 저장 및 결과 반환
        new_document = Document.objects.create(
            type=doc_type,
            content=generated_content
        )

        return Response(
            DocumentResponseSerializer(new_document).data,
            status=status.HTTP_201_CREATED
        )

    @swagger_auto_schema(
        operation_summary="AI 기반 법률 문서 수정",
        operation_description="document_id로 조회한 기존 문서를 사용자의 요청에 따라 AI가 재작성합니다.",
        request_body=DocumentPatchRequestSerializer,
        responses={200: DocumentResponseSerializer()}
    )
    def patch(self, request, *args, **kwargs):
        # 1. 시리얼라이저 검증
        serializer = DocumentPatchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        document_id = serializer.validated_data.get('document_id')
        user_request = serializer.validated_data.get('user_request')

        # 2. DB에서 기존 문서 조회 (get_object_or_404 대신 직접 예외 처리)
        try:
            document = Document.objects.get(document_id=document_id, is_deleted=False)
        except Document.DoesNotExist:
            return Response({"error": f"ID {document_id} 문서를 찾을 수 없습니다."}, status=404)

        # 3. LangChain 서비스 호출
        try:
            updated_content = edit_legal_document_with_ai(
                original_content=document.content,
                user_request=user_request
            )

            # 4. 결과 업데이트 및 저장
            document.content = updated_content
            document.save()

            return Response(DocumentResponseSerializer(document).data, status=200)

        except Exception as e:
            return Response({"error": f"AI 수정 중 오류 발생: {str(e)}"}, status=500)