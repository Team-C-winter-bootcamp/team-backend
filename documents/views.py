import json
import time

from django.http import StreamingHttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.renderers import BaseRenderer, JSONRenderer
from drf_yasg.utils import swagger_auto_schema
import google.genai as genai
from .models import Template, Document
from cases.models import Case
from .service import generate_legal_document, edit_legal_document_with_ai
from .serializers import (
    DocumentCreateRequestSerializer,
    DocumentResponseSerializer,
    DocumentPatchRequestSerializer
)

# Swagger 설정 딕셔너리 (Protected 멤버 접근 경고 방지)
SWAGGER_DOCS = {
    "post": {
        "request_body": DocumentCreateRequestSerializer,
        "responses": {201: DocumentResponseSerializer(), 404: "사건/템플릿 없음"}
    },
    "patch": {
        "request_body": DocumentPatchRequestSerializer,
        "responses": {200: DocumentResponseSerializer()}
    }
}


class SSEStreamRenderer(BaseRenderer):
    media_type = "text/event-stream"
    format = "event-stream"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


class BaseLegalDocumentView(APIView):
    renderer_classes = (JSONRenderer, SSEStreamRenderer)
    doc_type = None
    doc_name_ko = ""

    def _sse(self, event, data):
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    def _iter_chunks(self, text, chunk_size=30):
        for i in range(0, len(text), chunk_size):
            yield text[i:i + chunk_size]
    def gemini_stream(message):
        model = genai.GenerativeModel("gemini-1.5-flash")

        stream = model.generate_content(message, stream=True)



    def post(self, request):
        serializer = DocumentCreateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        case_id = serializer.validated_data.get('case_id')
        precedent = serializer.validated_data.get('precedent', "")

        try:
            case_obj = Case.objects.get(id=case_id, is_deleted=False)
            template = Template.objects.get(type=self.doc_type, is_deleted=False)
        except (Case.DoesNotExist, Template.DoesNotExist):
            return Response({"error": f"{self.doc_name_ko} 관련 정보를 찾을 수 없습니다."}, status=404)

        case_info = f"대상:{case_obj.who}, 일시:{case_obj.when}, 내용:{case_obj.what}, 상세:{case_obj.detail}"

        response = StreamingHttpResponse(
            self._stream_generation(case_info, precedent, template.content),
            content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def patch(self, request):
        serializer = DocumentPatchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doc_id = serializer.validated_data.get('document_id')
        user_request = serializer.validated_data.get('user_request')

        try:
            # 조회 조건에 type=self.doc_type을 추가하여 검증을 강화합니다.
            document = Document.objects.get(
                document_id=doc_id,
                type=self.doc_type,  # 접속한 API의 타입과 일치하는지 확인
                is_deleted=False
            )

        except Document.DoesNotExist:
            # ID가 아예 없거나, ID는 있지만 타입이 다른 경우 모두 여기서 걸립니다.
            return Response(
                {"error": f"ID {doc_id}에 해당하는 {self.doc_name_ko} 문서를 찾을 수 없습니다."},
                status=status.HTTP_404_NOT_FOUND
            )

        response = StreamingHttpResponse(
            self._stream_edit(document, user_request),
            content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    def _stream_generation(self, case_info, precedent, template_content):
        try:
            content = generate_legal_document(case_info, precedent, template_content, self.doc_type)
            for chunk in self._iter_chunks(content):
                yield self._sse("message", {"content": chunk})
                time.sleep(0.01)

            new_doc = Document.objects.create(type=self.doc_type, content=content)
            yield self._sse("done", {"result": DocumentResponseSerializer(new_doc).data})
        except Exception as e:
            yield self._sse("error", {"error": str(e)})

    def _stream_edit(self, document, user_request):
        try:
            content = edit_legal_document_with_ai(document.content, user_request)
            for chunk in self._iter_chunks(content):
                yield self._sse("message", {"content": chunk})
                time.sleep(0.01)

            document.content = content
            document.save()
            yield self._sse("done", {"result": DocumentResponseSerializer(document).data})
        except Exception as e:
            yield self._sse("error", {"error": str(e)})


# --- 상속받은 전용 View 클래스들 ---

class ComplaintView(BaseLegalDocumentView):
    doc_type, doc_name_ko = 'complaint', "고소장"

    @swagger_auto_schema(operation_summary=f"{doc_name_ko} AI 생성", **SWAGGER_DOCS["post"])
    def post(self, request): return super().post(request)

    @swagger_auto_schema(operation_summary=f"{doc_name_ko} AI 수정", **SWAGGER_DOCS["patch"])
    def patch(self, request): return super().patch(request)


class NoticeView(BaseLegalDocumentView):
    doc_type, doc_name_ko = 'notice', "내용증명서"

    @swagger_auto_schema(operation_summary=f"{doc_name_ko} AI 생성", **SWAGGER_DOCS["post"])
    def post(self, request): return super().post(request)

    @swagger_auto_schema(operation_summary=f"{doc_name_ko} AI 수정", **SWAGGER_DOCS["patch"])
    def patch(self, request): return super().patch(request)


class AgreementView(BaseLegalDocumentView):
    doc_type, doc_name_ko = 'agreement', "합의서"

    @swagger_auto_schema(operation_summary=f"{doc_name_ko} AI 생성", **SWAGGER_DOCS["post"])
    def post(self, request): return super().post(request)

    @swagger_auto_schema(operation_summary=f"{doc_name_ko} AI 수정", **SWAGGER_DOCS["patch"])
    def patch(self, request): return super().patch(request)