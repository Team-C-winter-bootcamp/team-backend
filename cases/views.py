from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

from .models import Case, Category
from .serializers import *
from .service import GeminiService, OpenSearchService

# 1. 초기 데이터 조회 (Init)
class InitDataAPIView(APIView):
    @swagger_auto_schema(
        operation_id="init_data",
        responses={
            200: InitDataSerializer(many=True),
            500: openapi.Response(description="서버 오류")
        },
        operation_summary="초기 데이터 조회 (카테고리 및 질문)",
        operation_description="프론트엔드 초기 렌더링 시 필요한 카테고리별 질문 리스트를 조회합니다.",
        tags=["cases"]
    )
    def get(self, request):
        try:
            # is_deleted가 False인 카테고리만 가져오기
            categories = Category.objects.filter(is_deleted=False).prefetch_related('questions')
            serializer = InitDataSerializer(categories, many=True)
            # 이전 에러 수정: status.status -> status
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            logging.error(f"Init Error: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 2. 유사 판례 검색 및 상황 저장 (Search)
class CaseSearchView(APIView):
    @swagger_auto_schema(
        operation_id="case_search",
        request_body=CaseSerializer,
        responses={
            201: CaseSearchResponseSerializer,
            500: openapi.Response(description="서버 오류")
        },
        operation_summary="유사 판례 검색 및 상황 저장",
        operation_description="사용자 상황을 입력받아 유사 판례를 검색하고 사건 정보를 저장합니다.",
        tags=["cases"]
    )
    def post(self, request):
        serializer = CaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        v_data = serializer.validated_data

        try:
            # 1. 카테고리 및 사건 저장
            category_obj, _ = Category.objects.get_or_create(name=v_data.get('category', '일반'))
            new_case = Case.objects.create(
                category=category_obj,
                who=v_data['who'],
                when=v_data['when'],
                what=v_data['what'],
                want=v_data['want'],
                detail=v_data['detail']
            )

            # 2. 임베딩 및 검색
            query_embedding = GeminiService.create_embedding(new_case.detail)
            precedents = OpenSearchService.search_similar_precedents(query_embedding, k=5)

            return Response({
                "status": "success",
                "code": 201,
                "message": "유사 판례 검색 완료",
                "data": {
                    "case_id": new_case.id,
                    "total_count": len(precedents),
                    "results": precedents
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logging.error(f"Search Error: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 3. 판례 상세 조회 및 AI 분석 (Detail)
class PrecedentDetailView(APIView):
    @swagger_auto_schema(
        operation_id="precedent_detail",
        manual_parameters=[
            openapi.Parameter(
                'precedents_id',
                openapi.IN_PATH,
                description="판례 사건번호",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        responses={
            200: PrecedentDetailResponseSerializer,
            404: openapi.Response(description="판례를 찾을 수 없습니다.")
        },
        operation_summary="판례 상세 조회 및 AI 분석",
        operation_description="사건번호로 판례 정보와 AI가 구조화한 요약 데이터를 조회합니다.",
        tags=["cases"]
    )
    def get(self, request, precedents_id):
        precedent = OpenSearchService.get_precedent_by_case_number(precedents_id)
        if not precedent:
            return Response({"message": "판례를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        # AI 요약 수행
        summary = GeminiService.summarize_precedent_langchain(precedent.get("content", ""))

        return Response({
            "status": "success",
            "data": {
                "case_no": precedent.get("case_no"),
                "court" : precedent.get("court"),
                "case_name": precedent.get("case_name"),
                "judgment_date": precedent.get("judgment_date"),
                "content": precedent.get("content"),
                "summary": summary
            }
        }, status=status.HTTP_200_OK)


# 4. 판례 기반 심층 분석 (Answer)
class CaseAnswerView(APIView):
    @swagger_auto_schema(
        operation_id="case_answer",
        manual_parameters=[
            openapi.Parameter(
                'precedents_id',
                openapi.IN_PATH,
                description="판례 사건번호",
                type=openapi.TYPE_STRING,
                required=True
            )
        ],
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['case_id'],
            properties={
                'case_id': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="저장된 사건 ID"
                )
            }
        ),
        responses={
            200: CaseAnswerApiResponseSerializer,
            404: openapi.Response(description="사건 또는 판례를 찾을 수 없습니다."),
            500: openapi.Response(description="서버 오류")
        },
        operation_summary="판례 기반 심층 분석",
        operation_description="저장된 사건과 판례를 기반으로 AI 심층 분석을 수행합니다.",
        tags=["cases"]
    )
    def post(self, request, precedents_id):
        case_id = request.data.get('case_id')
        try:
            case_obj = Case.objects.get(id=case_id)
            precedent = OpenSearchService.get_precedent_by_case_number(precedents_id)

            if not precedent:
                return Response({"error": "판례 정보 없음"}, status=status.HTTP_404_NOT_FOUND)

            # 심층 분석 실행
            analysis = GeminiService.analyze_case_deeply(
                {"who": case_obj.who, "detail": case_obj.detail},
                precedent.get("content", "")
            )

            return Response({"status": "success", "data": analysis}, status=status.HTTP_200_OK)
        except Case.DoesNotExist:
            return Response({"error": "사건 ID를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
