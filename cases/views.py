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
                schema=CaseResultSerializer,
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
    """
    특정 판례의 전문과 AI 요약을 조회하는 API
    GET /api/cases/{cases_id}/{precedents_id}
    """
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: PrecedentDetailResponseSerializer,
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
    def get(self, request, cases_id, precedents_id, *args, **kwargs):
        """
        판례 전문과 AI 요약을 조회합니다.
        
        Args:
            cases_id: Case 모델의 ID (현재는 사용하지 않지만 URL 구조상 필요)
            precedents_id: 사건번호 (caseNo)
        """
        try:
            # 1. OpenSearch 연결 확인
            if not OpenSearchService.check_connection():
                raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")
            
            # 2. precedents_id는 사건번호(caseNo)
            case_no = precedents_id
            
            # 3. 판례 전문 조회
            precedent = OpenSearchService.get_precedent_by_case_number(case_no)
            
            if not precedent:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_404_NOT_FOUND,
                        "message": f"사건번호 '{case_no}'에 해당하는 판례를 찾을 수 없습니다."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 4. 판례 내용 추출
            precedent_content = precedent.get("판례내용", "")
            
            if not precedent_content:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_404_NOT_FOUND,
                        "message": "판례 내용이 없습니다."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 5. AI 요약 생성 (LangChain 사용)
            try:
                ai_summary = GeminiService.summarize_precedent_langchain(precedent_content)
            except Exception as e:
                logging.error(f"AI 요약 생성 실패: {type(e).__name__}: {str(e)}", exc_info=True)
                # 실제 오류 메시지를 포함하여 디버깅 용이하게
                ai_summary = f"요약 생성 중 오류가 발생했습니다: {str(e)[:200]}"
            
            # 6. 응답 데이터 구성
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
            
        except ConnectionError as e:
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "message": str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except Exception as e:
            logging.error(f"판례 상세 조회 중 오류 발생: {e}", exc_info=True)
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": f"서버 내부 오류가 발생했습니다: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



class CaseAnswerView(APIView):
    """
    여러 판례 번호를 기반으로 종합적인 법률 솔루션을 생성하는 API
    """
    @swagger_auto_schema(
        request_body=CaseAnswerPostRequestSerializer,
        responses={
            status.HTTP_200_OK: CaseAnswerApiResponseSerializer,
            status.HTTP_400_BAD_REQUEST: "잘못된 요청 형식입니다.",
            status.HTTP_404_NOT_FOUND: "일부 또는 전체 판례를 찾을 수 없습니다.",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "서버 내부 오류가 발생했습니다."
        },
        operation_summary="종합 판례 분석 및 솔루션 제공 API",
        operation_description=(
            "판례 번호 리스트를 POST하면, 해당 판례들을 OpenSearch에서 조회하고 Gemini를 통해 종합 분석하여, "
            "구체적인 법률 솔루션(결과 예측, 실행 로드맵, 증거 전략, 법적 근거)을 구조화된 JSON 형태로 반환합니다."
        ),
        tags=["cases"]
    )
    def post(self, request, case_id, *args, **kwargs):
        print(f"DEBUG: CaseAnswerView post method hit for case_id: {case_id}")
        serializer = CaseAnswerPostRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            case_nos = serializer.validated_data['case_no']
            if not case_nos:
                return Response(
                    {"status": "error", "message": "판례 번호 목록이 비어 있습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 1. OpenSearch 연결 확인
            if not OpenSearchService.check_connection():
                raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")

            # 2. 여러 판례 한 번에 조회
            precedents = OpenSearchService.get_precedents_by_case_numbers(case_nos)
            
            if not precedents:
                return Response(
                    {"status": "error", "message": "요청된 판례를 하나도 찾을 수 없습니다.", "searched_case_nos": case_nos},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 3. 판례 내용 추출
            precedent_contents = [p.get("판례내용", "") for p in precedents if p.get("판례내용")]
            if not precedent_contents:
                return Response(
                    {"status": "error", "message": "조회된 판례 중에 유효한 내용이 없습니다."},
                    status=status.HTTP_404_NOT_FOUND
                )

            # 4. Gemini를 통해 종합 분석 수행
            analysis_result = GeminiService.generate_answer_from_precedents(precedent_contents)

            if "error" in analysis_result:
                return Response(
                    {"status": "error", "message": "AI 분석 중 오류가 발생했습니다.", "details": analysis_result.get("details")},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

            # 5. 응답 데이터 구성
            analysis_result['case_id'] = f"LAW-{case_id}"

            response_data = {
                "status": "success",
                "data": analysis_result
            }

            # 6. 응답 데이터 유효성 검사
            response_serializer = CaseAnswerApiResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except ConnectionError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except NotFoundError as e:
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logging.error(f"종합 판례 분석 중 오류 발생: {e}", exc_info=True)
            return Response(
                {"status": "error", "message": f"서버 내부 오류가 발생했습니다: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
