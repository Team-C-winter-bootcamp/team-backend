from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from .models import Precedent
from .serializers import PrecedentListSerializer, PrecedentDetailSerializer


class PrecedentListView(APIView):
    @swagger_auto_schema(
        operation_summary="판례 목록 조회 및 검색",
        operation_description="판례 목록을 조회합니다. 키워드 검색, 카테고리 필터링, 법원 필터링을 지원합니다.",
        tags=["판례"],
        manual_parameters=[
            openapi.Parameter(
                'q',
                openapi.IN_QUERY,
                description="검색 키워드 (판례의 키워드와 부분 일치 검색)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'categories',
                openapi.IN_QUERY,
                description="카테고리 ID (소분류)",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'court',
                openapi.IN_QUERY,
                description="법원 코드",
                type=openapi.TYPE_INTEGER,
                required=False
            ),
            openapi.Parameter(
                'outcome_display',
                openapi.IN_QUERY,
                description="판결 결과 (예: 기각, 인용, 파기환송)",
                type=openapi.TYPE_STRING,
                required=False
            ),
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="페이지 번호",
                type=openapi.TYPE_INTEGER,
                required=False,
                default=1
            ),
            openapi.Parameter(
                'limit',
                openapi.IN_QUERY,
                description="페이지당 항목 수",
                type=openapi.TYPE_INTEGER,
                required=False,
                default=10
            ),
        ],
        responses={
            200: openapi.Response(
                description="판례 목록 조회 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="PRE_200"),
                        "status": openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="판례 키워드 검색 성공"),
                        "meta": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "total_count": openapi.Schema(type=openapi.TYPE_INTEGER, example=100),
                                "page": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                "limit": openapi.Schema(type=openapi.TYPE_INTEGER, example=10),
                            }
                        ),
                        "data": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "precedents_id": openapi.Schema(type=openapi.TYPE_INTEGER, example=1),
                                    "case_title": openapi.Schema(type=openapi.TYPE_STRING, example="손해배상청구 사건"),
                                    "case_preview": openapi.Schema(type=openapi.TYPE_STRING, example="원고는 피고를 상대로 손해배상을 청구하였다..."),
                                    "outcome_display": openapi.Schema(type=openapi.TYPE_STRING, example="결과 없음"),
                                }
                            )
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        # 1. 기본 쿼리셋 준비
        queryset = Precedent.objects.all()

        # 2. 쿼리 파라미터 추출
        search_query = request.query_params.get('q')  # 키워드 검색어
        category_id = request.query_params.get('categories')  # 카테고리 ID
        court_code = request.query_params.get('court')  # 법원 코드
        outcome_display = request.query_params.get('outcome_display')  # 판결 결과

        # 3. 다대다(M2M) 키워드 필터링 적용
        if search_query:
            # keywords: Precedent 모델의 M2M 필드명
            # name: Keyword 모델의 실제 단어 필드명
            # distinct(): 다대다 조인 시 발생하는 중복 데이터 제거
            queryset = queryset.filter(keywords__name__icontains=search_query).distinct()

        # 4. 기타 필터링
        if category_id:
            queryset = queryset.filter(subcategory_id=category_id)
        if court_code:
            queryset = queryset.filter(court__court_code=court_code)
        if outcome_display:
            queryset = queryset.filter(relationoutcome__outcome__outcome_type=outcome_display)

        # 5. N+1 쿼리 방지를 위한 select_related (1대1 관계이므로 select_related 사용)
        queryset = queryset.select_related('relationoutcome__outcome')

        # 6. 직렬화 및 응답
        serializer = PrecedentListSerializer(queryset, many=True)
        return Response({
            "code": "PRE_200",
            "status": 200,
            "message": "판례 키워드 검색 성공",
            "meta": {
                "total_count": queryset.count(),
                "page": int(request.query_params.get('page', 1)),
                "limit": int(request.query_params.get('limit', 10)),
            },
            "data": serializer.data
        })


class PrecedentDetailView(APIView):
    @swagger_auto_schema(
        operation_summary="판례 상세 조회",
        operation_description="특정 판례의 상세 정보를 조회합니다. 사건 제목, 사건명, 판결내용, 판결요지, 판시사항, 질문, 답변, 요약원문, 요약을 반환합니다.",
        tags=["판례"],
        manual_parameters=[
            openapi.Parameter(
                'id',
                openapi.IN_PATH,
                description="판례 ID",
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="판례 상세 조회 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="DET_200"),
                        "status": openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                        "message": openapi.Schema(type=openapi.TYPE_STRING, example="판례 상세 조회 성공"),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "case_title": openapi.Schema(type=openapi.TYPE_STRING, example="손해배상청구 사건"),
                                "case_name": openapi.Schema(type=openapi.TYPE_STRING, example="○○ 대 ○○"),
                                "full_text": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="【판결요지】 원고의 청구를 기각한다. 【이유】 ..."
                                ),
                                "judgment_summary": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="판결요지 내용입니다."
                                ),
                                "holdings": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="판시사항 내용입니다."
                                ),
                                "question": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="질문 내용입니다."
                                ),
                                "answer": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="답변 내용입니다."
                                ),
                                "summary_original": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="요약원문 내용입니다."
                                ),
                                "summary": openapi.Schema(
                                    type=openapi.TYPE_STRING,
                                    example="요약 내용입니다."
                                ),
                            }
                        )
                    }
                )
            ),
            404: openapi.Response(description="판례를 찾을 수 없음")
        }
    )
    def get(self, request, id):
        # 상세 조회 (3개 필드만 반환됨)
        instance = get_object_or_404(Precedent, id=id)
        serializer = PrecedentDetailSerializer(instance)
        return Response({
            "code": "DET_200",
            "status": 200,
            "message": "판례 상세 조회 성공",
            "data": serializer.data
        })


class PrecedentInitView(APIView):
    @swagger_auto_schema(
        operation_summary="판례 초기 데이터 조회",
        operation_description="프론트엔드에서 사용할 초기 설정 데이터를 조회합니다. 법원 목록, 카테고리 목록, 판결 결과 목록을 반환합니다.",
        tags=["판례"],
        responses={
            200: openapi.Response(
                description="초기 데이터 조회 성공",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "code": openapi.Schema(type=openapi.TYPE_STRING, example="INIT_200"),
                        "status": openapi.Schema(type=openapi.TYPE_INTEGER, example=200),
                        "data": openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                "courts": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING),
                                    example=["대법원", "서울고등법원", "부산지방법원"]
                                ),
                                "categories": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING),
                                    example=["민사", "형사", "행정"]
                                ),
                                "outcomes": openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING),
                                    example=["기각", "인용", "파기환송"]
                                ),
                            }
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        # 프론트엔드 초기 설정 데이터
        mapping_data = {
            "courts": ["대법원", "서울고등법원", "부산지방법원"],
            "categories": ["민사", "형사", "행정"],
            "outcomes": ["기각", "인용", "파기환송"]
        }
        return Response({
            "code": "INIT_200",
            "status": 200,
            "message": "초기 데이터 조회 성공",
            "data": mapping_data
        })