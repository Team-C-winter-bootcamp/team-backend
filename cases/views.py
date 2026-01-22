import os
import json
from pathlib import Path
import google.generativeai as genai
from opensearchpy import OpenSearch, NotFoundError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from drf_yasg.utils import swagger_auto_schema
from .serializers import RAGSearchRequestSerializer

# --- 기존 뷰 ---
class HelloCasesView(APIView):
    def get(self, request):
        return Response({"message": "Hello from the cases app!"})

# --- RAG 테스트를 위한 뷰 (색인 및 검색 분리) ---

# --- 설정 ---
OPENSEARCH_HOST = "http://opensearch:9200"
INDEX_NAME = "law_rag_cases_test_index_v2"
EMBEDDING_MODEL = 'models/text-embedding-004'
BASE_DIR = Path(__file__).resolve().parent.parent
JSON_FILE_PATH = BASE_DIR / "data" / "2022도4719.json"
CONTENT_FIELD = "content"


def initialize_gemini():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)

def get_opensearch_client():
    return OpenSearch(OPENSEARCH_HOST)


class RAGIngestView(APIView):
    """
    POST 요청을 통해 하드코딩된 JSON 파일을 OpenSearch에 색인합니다.
    """
    def post(self, request, *args, **kwargs):
        try:
            initialize_gemini()
            client = get_opensearch_client()
        except (ValueError, Exception) as e:
            return Response({"error": f"초기화 실패: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            embedding_dimension = 768
            if client.indices.exists(index=INDEX_NAME):
                client.indices.delete(index=INDEX_NAME)
            
            index_body = {
                "settings": {"index": {"knn": True}},
                "mappings": {
                    "properties": {
                        "embedding": {"type": "knn_vector", "dimension": embedding_dimension},
                        CONTENT_FIELD: {"type": "text"}
                    }
                }
            }
            client.indices.create(index=INDEX_NAME, body=index_body)
        except Exception as e:
            return Response({"error": f"인덱스 생성 실패: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            with open(JSON_FILE_PATH, 'r', encoding='utf-8') as f:
                doc = json.load(f)

            jdgmn_text = doc.get("jdgmn", "")
            summary_list = doc.get("Summary", [])
            summ_contxt_text = ""
            if summary_list and isinstance(summary_list, list) and len(summary_list) > 0:
                summ_contxt_text = summary_list[0].get("summ_contxt", "")

            text_to_embed = f"판결요지: {jdgmn_text}\n\n요약내용: {summ_contxt_text}"

            if not text_to_embed.strip() or (not jdgmn_text and not summ_contxt_text):
                 raise ValueError("JSON 파일에서 임베딩할 텍스트 필드('jdgmn', 'Summary')를 찾을 수 없습니다.")

            result = genai.embed_content(model=EMBEDDING_MODEL, content=text_to_embed, task_type="RETRIEVAL_DOCUMENT")
            embedding = result['embedding']
            
            document_to_index = { "embedding": embedding, CONTENT_FIELD: text_to_embed } 
            
            doc_id = doc.get("info", {}).get("caseNo", os.path.basename(JSON_FILE_PATH).replace('.json', ''))
            client.index(index=INDEX_NAME, id=doc_id, body=document_to_index, refresh=True)
            
            return Response({"message": f"문서 '{doc_id}'를 성공적으로 색인했습니다."}, status=status.HTTP_201_CREATED)

        except FileNotFoundError:
            return Response({"error": f"데이터 파일을 찾을 수 없습니다: {JSON_FILE_PATH}"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"문서 색인 실패: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RAGSearchView(APIView):
    """
    POST 요청으로 받은 JSON 본문을 기반으로 RAG 검색을 수행합니다.
    """
    @swagger_auto_schema(request_body=RAGSearchRequestSerializer)
    def post(self, request, *args, **kwargs):
        serializer = RAGSearchRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = serializer.validated_data
        category = validated_data.get("category")
        situation = validated_data.get("situation", {})

        search_text_parts = [f"카테고리: {category}"]
        situation_details = [v for k, v in situation.items() if k != "detail"]
        search_text_parts.append(f"상황: {', '.join(situation_details)}")
        if "detail" in situation:
            search_text_parts.append(f"상세 정보: {situation['detail']}")
        
        search_text = ". ".join(search_text_parts)

        try:
            initialize_gemini()
            client = get_opensearch_client()
        except (ValueError, Exception) as e:
            return Response({"error": f"초기화 실패: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            result = genai.embed_content(model=EMBEDDING_MODEL, content=search_text, task_type="RETRIEVAL_QUERY")
            query_embedding = result['embedding']
            
            knn_query = {
                "size": 3,
                "query": {"knn": {"embedding": {"vector": query_embedding, "k": 3}}}
            }
            
            response = client.search(index=INDEX_NAME, body=knn_query)
            
            results = []
            for hit in response['hits']['hits']:
                results.append({
                    "score": hit['_score'],
                    "content": hit['_source'].get(CONTENT_FIELD)
                })
            
            return Response({"search_text": search_text, "results": results}, status=status.HTTP_200_OK)
        
        except NotFoundError:
            return Response({"error": f"인덱스 '{INDEX_NAME}'를 찾을 수 없습니다. 먼저 POST /api/cases/rag-ingest/ 로 데이터를 색인해주세요."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": f"검색 실패: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)