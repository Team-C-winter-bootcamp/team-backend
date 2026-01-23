from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from opensearchpy import NotFoundError
import logging

from .models import Case, Category
from .serializers import (
    CaseSearchRequestSerializer,
    CaseSearchResponseSerializer,
    CaseAnswerRequestSerializer,
    CaseAnswerResponseSerializer,
    PrecedentDetailResponseSerializer,
    CaseAnalysisResponseSerializer
)
from .service import GeminiService, OpenSearchService


class CaseSearchView(APIView):
    """
    사용자의 상황 설명을 기반으로 유사한 판례를 검색하는 API
    """
    @swagger_auto_schema(
        request_body=CaseSearchRequestSerializer,
        responses={
            status.HTTP_201_CREATED: CaseSearchResponseSerializer,
            status.HTTP_400_BAD_REQUEST: "잘못된 요청 형식입니다.",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "서버 내부 오류가 발생했습니다."
        },
        operation_summary="유사 판례 검색 API",
        operation_description=(
            "사용자가 처한 상황(카테고리, 질문에 대한 답변, 상세 설명)을 JSON 형태로 POST하면, "
            "이를 바탕으로 가장 유사한 판례 4개를 검색하여 반환합니다."
        ),
        tags=["cases"]
    )
    def post(self, request, *args, **kwargs):
        serializer = CaseSearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. OpenSearch 연결 확인
            if not OpenSearchService.check_connection():
                raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")

            # 2. 검색어 생성
            validated_data = serializer.validated_data
            category = validated_data["category"]
            situation = validated_data["situation"]
            
            situation_text = ", ".join(situation.values())
            search_query = f"카테고리: {category}. 상황: {situation_text}"

            # 3. 검색어 임베딩 생성
            query_embedding = GeminiService.create_embedding(
                content=search_query
            )

            # 4. 유사 판례 검색
            precedents = OpenSearchService.search_similar_precedents(
                query_embedding=query_embedding,
                k=4,
                size=50  # 중복 제거를 위해 충분한 수의 결과 가져오기
            )
            
            # 5. Case 모델에 데이터 저장
            # Category 찾기 또는 생성
            category_obj, created = Category.objects.get_or_create(
                name=category,
                defaults={'is_deleted': False}
            )
            
            # user_info에 request 데이터 전체 저장
            user_info_data = {
                "category": category,
                "situation": situation
            }
            
            # Case 인스턴스 생성 및 저장
            case = Case.objects.create(
                category=category_obj,
                user_info=user_info_data,
                is_deleted=False
            )
            
            # 6. 응답 데이터 구성
            response_data = {
                "status": "success",
                "code": status.HTTP_201_CREATED,
                "message": "유사 판례 검색이 완료되었습니다.",
                "data": {
                    "total_count": len(precedents),
                    "results": precedents
                }
            }
            
            # 응답 Serializer를 통해 데이터 유효성 검사
            response_serializer = CaseSearchResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except ConnectionError as e:
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "message": str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except NotFoundError as e:
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_404_NOT_FOUND,
                    "message": str(e)
                },
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logging.error(f"유사 판례 검색 중 오류 발생: {e}", exc_info=True)
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": f"검색 중 예기치 않은 오류가 발생했습니다: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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


class CaseAnalysisView(APIView):
    """
    사건 심층 분석 API
    GET /api/cases/{case_id}/{precedents_id}/answer/
    사용자의 상황을 바탕으로 4가지 핵심 영역(결과 예측, 행동 지침, 증거 전략, 법적 근거)으로 나누어 분석 결과를 제공합니다.
    """
    @swagger_auto_schema(
        responses={
            status.HTTP_200_OK: CaseAnalysisResponseSerializer,
            status.HTTP_400_BAD_REQUEST: "잘못된 요청 형식입니다.",
            status.HTTP_404_NOT_FOUND: "사건을 찾을 수 없습니다.",
            status.HTTP_500_INTERNAL_SERVER_ERROR: "서버 내부 오류가 발생했습니다."
        },
        operation_summary="사건 심층 분석 API",
        operation_description=(
            "사건 ID와 판례 ID를 기반으로 사용자의 상황을 분석하여 "
            "결과 예측, 행동 지침, 증거 전략, 법적 근거를 구조화된 형태로 제공합니다."
        ),
        tags=["cases"]
    )
    def get(self, request, case_id, precedents_id, *args, **kwargs):
        """
        사건 심층 분석을 수행합니다.
        
        Args:
            case_id: Case 모델의 ID
            precedents_id: 판례 ID (사건번호)
        """
        try:
            # 1. Case 모델에서 사건 조회
            try:
                case = Case.objects.get(id=case_id, is_deleted=False)
            except Case.DoesNotExist:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_404_NOT_FOUND,
                        "message": f"사건 ID '{case_id}'에 해당하는 사건을 찾을 수 없습니다."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 2. 사용자 상황 정보 추출
            user_info = case.user_info
            if not user_info:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_400_BAD_REQUEST,
                        "message": "사건에 사용자 상황 정보가 없습니다."
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 3. OpenSearch 연결 확인
            if not OpenSearchService.check_connection():
                raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")
            
            # 4. precedents_id로 지정된 판례 조회 (사건번호)
            selected_precedent = None
            case_no = precedents_id
            try:
                precedent_doc = OpenSearchService.get_precedent_by_case_number(case_no)
                if precedent_doc:
                    selected_precedent = {
                        "id": precedent_doc.get("판례일련번호"),
                        "case_number": precedent_doc.get("caseNo", ""),
                        "case_title": precedent_doc.get("caseTitle", ""),
                        "law_category": precedent_doc.get("사건종류명", ""),
                        "law_subcategory": precedent_doc.get("instance_name", ""),
                        "court": precedent_doc.get("courtNm", ""),
                        "judgment_date": precedent_doc.get("judmnAdjuDe", ""),
                        "similarity_score": 1.0,  # 선택된 판례는 최고 유사도로 설정
                        "preview": precedent_doc.get("summ_contxt", ""),
                    }
            except Exception as e:
                logging.warning(f"지정된 판례 조회 실패 (precedents_id={precedents_id}): {str(e)}")
                # 판례 조회 실패해도 계속 진행 (유사 판례 검색으로 대체)
            
            # 5. 유사 판례 검색을 위한 검색어 생성
            category = user_info.get("category", "")
            situation = user_info.get("situation", {})
            situation_text = ", ".join(situation.values()) if isinstance(situation, dict) else str(situation)
            search_query = f"카테고리: {category}. 상황: {situation_text}"
            
            # 6. 검색어 임베딩 생성
            query_embedding = GeminiService.create_embedding(content=search_query)
            
            # 7. 유사 판례 검색
            similar_precedents = OpenSearchService.search_similar_precedents(
                query_embedding=query_embedding,
                k=4,
                size=50
            )
            
            # 8. 선택된 판례를 유사 판례 리스트의 첫 번째로 추가
            if selected_precedent:
                # 이미 리스트에 있는지 확인 (case_number로 비교)
                existing_ids = {p.get("case_number") for p in similar_precedents}
                if selected_precedent.get("case_number") not in existing_ids:
                    # 선택된 판례를 첫 번째로 추가
                    similar_precedents.insert(0, selected_precedent)
                    # 최대 4개 유지
                    similar_precedents = similar_precedents[:4]
                else:
                    # 이미 있으면 첫 번째로 이동
                    similar_precedents = [p for p in similar_precedents if p.get("case_number") != selected_precedent.get("case_number")]
                    similar_precedents.insert(0, selected_precedent)
            
            if not similar_precedents:
                return Response(
                    {
                        "status": "error",
                        "code": status.HTTP_404_NOT_FOUND,
                        "message": "유사한 판례를 찾을 수 없습니다."
                    },
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 9. 심층 분석 수행
            analysis_result = GeminiService.analyze_case_deeply(
                user_situation=user_info,
                similar_precedents=similar_precedents
            )
            
            # 10. 분석 결과 정리 (누락된 필드 보완)
            analysis_result = CaseAnalysisView._ensure_complete_analysis_data(analysis_result)
            
            # 11. 응답 데이터 구성
            response_data = {
                "status": "success",
                "code": status.HTTP_200_OK,
                "message": "사건 심층 분석이 완료되었습니다.",
                "data": analysis_result
            }
            
            # 12. 응답 Serializer를 통해 데이터 유효성 검사
            response_serializer = CaseAnalysisResponseSerializer(data=response_data)
            if not response_serializer.is_valid():
                # 검증 실패 시 로깅하고 기본 구조로 대체
                logging.warning(f"Serializer 검증 실패: {response_serializer.errors}")
                response_data["data"] = GeminiService._get_default_analysis_structure()
                response_serializer = CaseAnalysisResponseSerializer(data=response_data)
                response_serializer.is_valid(raise_exception=True)
            
            return Response(response_serializer.data, status=status.HTTP_200_OK)
            
        except ConnectionError as e:
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_503_SERVICE_UNAVAILABLE,
                    "message": str(e)
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        except ValueError as e:
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_400_BAD_REQUEST,
                    "message": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logging.error(f"사건 심층 분석 중 오류 발생: {e}", exc_info=True)
            return Response(
                {
                    "status": "error",
                    "code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                    "message": f"서버 내부 오류가 발생했습니다: {str(e)}"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @staticmethod
    def _ensure_complete_analysis_data(data):
        """분석 결과 데이터에서 누락된 필드를 보완합니다."""
        if not isinstance(data, dict):
            return GeminiService._get_default_analysis_structure()
        
        # legal_foundation.relevant_precedents의 각 항목에 key_points 보완
        if "legal_foundation" in data and isinstance(data["legal_foundation"], dict):
            legal = data["legal_foundation"]
            if "relevant_precedents" in legal and isinstance(legal["relevant_precedents"], list):
                for prec in legal["relevant_precedents"]:
                    if isinstance(prec, dict):
                        if "key_points" not in prec or not isinstance(prec.get("key_points"), list):
                            prec["key_points"] = []
                        if "relevance" not in prec:
                            prec["relevance"] = ""
        
        return data
