from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from opensearchpy import NotFoundError
import logging

from drf_yasg import openapi
from wrapt.importer import when_imported

from .models import Case, Category
from .serializers import *
from .service import GeminiService, OpenSearchService


class CaseSearchView(APIView):
    @swagger_auto_schema(
        request_body=CaseSerializer,
        responses={
            201: openapi.Response(
                description="검색 성공",
                schema=CaseAnswerApiResponseSerializer,
                examples={
                    "application/json": {
                        "status": "success",
                        "code": 201,
                        "message": "유사 판례 검색이 완료되었습니다.",
                        "data": {
                            "case_id": 1,
                            "total_count": 5,
                            "results": [
                                {"title": "2023도1234 판례", "score": 0.95},
                                {"title": "2022고단567 판례", "score": 0.88}
                            ]
                        }
                    }
                }
            ),
            400: "잘못된 요청 데이터",
            500: "서버 내부 오류"
        },
        operation_summary="유사 판례 검색 및 상황 저장",
        tags=["cases"]
    )
    def post(self, request):
        serializer = CaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        v_data = serializer.validated_data

        try:
            category_obj, _ = Category.objects.get_or_create(name=v_data['category'])
            new_case = Case.objects.create(
                category=category_obj,
                who=v_data['who'],
                when=v_data['when'],
                what=v_data['what'],
                want=v_data['want'],
                detail=v_data['detail']
            )

            query_embedding = GeminiService.create_embedding(new_case.detail)

            precedents = OpenSearchService.search_similar_precedents(
                query_embedding=query_embedding,
                k=5
            )
            response_payload = {
                "status": "success",
                "code": 201,
                "message": "유사 판례 검색이 완료되었습니다.",
                "data": {
                    "case_id": new_case.id,
                    "total_count": len(precedents),
                    "results": precedents
                }
            }

            return Response(response_payload, status=status.HTTP_201_CREATED)

        except Exception as e:
            logging.error(f"Case Search Error: {str(e)}")
            return Response({
                "status": "error",
                "message": f"처리 중 오류가 발생했습니다: {str(e)}"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PrecedentDetailView(APIView):
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK:CaseAnswerApiResponseSerializer,
            status.HTTP_404_NOT_FOUND: "판례를 찾을 수 없습니다.",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "서버 내부 오류가 발생했습니다."
        },
        operation_summary="판례 상세 조회 API",
        operation_description=(
            "사건번호(precedents_id)를 기반으로 판례 전문을 조회하고, "
            "Gemini AI를 사용하여 판례를 요약합니다."
        ),
        tags=["cases"]
    )
    def get(self, request, precedents_id, *args, **kwargs):

        if not OpenSearchService.check_connection():
            raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")

        precedent = OpenSearchService.get_precedent_by_case_number(precedents_id)

        precedent_content = precedent.get("content", "")

        ai_summary = GeminiService.summarize_precedent_langchain(precedent_content)

        response_data = {
            "status": "success",
            "code": status.HTTP_200_OK,
            "message": "판례 상세 정보를 성공적으로 조회했습니다.",
            "data": {
                "case_number": precedent.get("caseNo", ""),
                "case_title": precedent.get("caseTitle", ""),
                "case_name": precedent.get("caseNm", ""),
                "court": precedent.get("courtNm", ""),
                "judgment_date": precedent.get("judmnAdjuDe", ""),
                "precedent_id": precedent.get("판례일련번호"),
                "issue": precedent.get("판시사항", ""),
                "holding": precedent.get("판결요지", ""),
                "content": precedent_content,
                "summary": ai_summary
            }
        }
            
        return Response(response_data, status=status.HTTP_200_OK)


class CaseAnswerView(APIView):
    @swagger_auto_schema(
        operation_summary="판례 기반 심층 분석",
        operation_description=(
                "사용자가 저장한 사건 ID(case_id)와 선택한 판례 번호(precedents_id)를 비교 분석합니다. "
                "Gemini 3 Pro 모델을 사용하여 승소 확률과 대응 로드맵을 생성합니다."
        ),
        manual_parameters=[
            openapi.Parameter(
                'precedents_id',
                openapi.IN_PATH,
                description="분석 기준이 되는 판례의 사건번호",
                type=openapi.TYPE_STRING,
                required=True,
                example="2021도1234"
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_id'],
            properties={
                'case_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="사용자 상황이 저장된 Case 테이블의 고유 ID",
                    example=1
                )
            }
        ),
        responses={
            200: CaseAnswerApiResponseSerializer,
            404: "사건 정보 또는 판례를 찾을 수 없음",
            503: "OpenSearch 서버 연결 실패"
        },
        tags=["cases"]
    )
    def post(self, request, precedents_id, *args, **kwargs):

        if not OpenSearchService.check_connection():
            return Response({"error": "OpenSearch 연결 실패"}, status=503)

        case_id = request.data.get('case_id')
        case_obj = Case.objects.get(id=case_id)

        user_situation = {
            'who': case_obj.who, 'when': case_obj.when,
            'what': case_obj.what, 'want': case_obj.want, 'detail': case_obj.detail
        }

        precedents = OpenSearchService.get_precedent_by_case_number(precedents_id)
        if not precedents:
            return Response({"error": "판례를 찾을 수 없습니다."}, status=404)

        analysis_result = GeminiService.analyze_case_deeply(user_situation, precedents.get("content", ""))

        final_response = {
            "status": "success",
            "data": analysis_result
        }

        return Response(final_response, status=status.HTTP_200_OK)
