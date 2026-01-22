import os
import google.generativeai as genai
from opensearchpy import OpenSearch, RequestsHttpConnection, NotFoundError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema

from .serializers import CaseSearchRequestSerializer, CaseSearchResponseSerializer

# --- 설정 ---
# index_precedents.py와 동일한 설정을 사용합니다.
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "opensearch")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 9200))
INDEX_NAME = "precedents_chunked"
EMBEDDING_MODEL = "models/text-embedding-004"


def initialize_gemini():
    """Gemini API 키를 환경 변수에서 읽어 초기화합니다."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)

def get_opensearch_client():
    """OpenSearch 클라이언트 인스턴스를 반환합니다."""
    return OpenSearch(
        hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
        http_conn_class=RequestsHttpConnection,
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
    )

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
        )
    )
    def post(self, request, *args, **kwargs):
        serializer = CaseSearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 1. 초기화
            initialize_gemini()
            opensearch_client = get_opensearch_client()
            if not opensearch_client.ping():
                raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")

            # 2. 검색어 생성
            validated_data = serializer.validated_data
            category = validated_data["category"]
            situation = validated_data["situation"]
            
            situation_text = ", ".join(situation.values())
            search_query = f"카테고리: {category}. 상황: {situation_text}"

            # 3. 검색어 임베딩
            embedding_result = genai.embed_content(
                model=EMBEDDING_MODEL,
                content=search_query,
                task_type="RETRIEVAL_QUERY"
            )
            query_embedding = embedding_result['embedding']

            # 4. OpenSearch k-NN 검색
            knn_query = {
                "size": 4, # 중복될 수 있으므로 일단 더 많이 가져옴 (예: 10개)
                "_source": {
                    "excludes": ["content_embedding"] # 임베딩 벡터는 제외하고 가져옴
                },
                "query": {
                    "knn": {
                        "content_embedding": {
                            "vector": query_embedding,
                            "k": 4
                        }
                    }
                }
            }
            
            response = opensearch_client.search(
                index=INDEX_NAME,
                body=knn_query
            )

            # 5. 결과 처리 (중복 판례 제거 및 점수가 가장 높은 청크 선택)
            unique_precedents = {}
            for hit in response['hits']['hits']:
                score = hit['_score']
                source = hit['_source']
                precedent_id = source['판례일련번호']

                if precedent_id not in unique_precedents or score > unique_precedents[precedent_id]['similarity_score']:
                    unique_precedents[precedent_id] = {
                        "id": precedent_id,
                        "case_number": source.get("caseNo"),
                        "case_title": source.get("caseTitle"),
                        "law_category": source.get("사건종류명"),
                        "law_subcategory": source.get("instance_name"),
                        "court": source.get("courtNm"),
                        "judgment_date": source.get("judmnAdjuDe"),
                        "similarity_score": score,
                        "preview": source.get("summ_contxt", ""), 
                    }

            # 유사도 점수 기준으로 내림차순 정렬
            sorted_results = sorted(unique_precedents.values(), key=lambda x: x['similarity_score'], reverse=True)
            
            # 최종 4개 선택
            final_results = sorted_results[:4]
            
            # 6. 응답 데이터 구성
            response_data = {
                "status": "success",
                "code": status.HTTP_201_CREATED,
                "message": "유사 판례 검색이 완료되었습니다.",
                "data": {
                    "total_count": len(final_results),
                    "results": final_results
                }
            }
            
            # 응답 Serializer를 통해 데이터 유효성 검사 (선택 사항이지만 좋은 습관)
            response_serializer = CaseSearchResponseSerializer(data=response_data)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except (ValueError, ConnectionError) as e:
            return Response({"status": "error", "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except NotFoundError:
            return Response({"status": "error", "message": f"인덱스 '{INDEX_NAME}'를 찾을 수 없습니다. 먼저 데이터 색인을 진행해주세요."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # 프로덕션 환경에서는 더 일반적인 오류 메시지를 사용하는 것이 좋습니다.
            return Response({"status": "error", "message": f"검색 중 예기치 않은 오류가 발생했습니다: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

