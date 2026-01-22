import os
import logging
from typing import List, Dict, Optional, Any

# LangChain 관련 임포트
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser

# OpenSearch 관련 임포트
from opensearchpy import OpenSearch, RequestsHttpConnection, NotFoundError
import google.genai as genai

# 설정 상수
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 9200))
CHUNKED_INDEX_NAME = "precedents_chunked"
PRECEDENTS_INDEX_NAME = "precedents"
EMBEDDING_MODEL = "models/text-embedding-004"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-1.5-pro") # 정확도를 위해 Pro 모델 권장

class GeminiService:
    """LangChain을 적용한 Gemini API 서비스 클래스"""
    
    _llm: Optional[ChatGoogleGenerativeAI] = None

    @classmethod
    def get_llm(cls, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
        """LangChain용 Gemini LLM 인스턴스를 반환합니다."""
        if cls._llm is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
            
            # 정확도를 위해 temperature를 낮게 설정(0.2~0.3)
            cls._llm = ChatGoogleGenerativeAI(
                model=GEMINI_MODEL.replace("models/", ""),
                google_api_key=api_key,
                temperature=temperature,
                max_output_tokens=2048, # 토큰 양을 충분히 확보
                top_p=0.95,
            )
        return cls._llm

    @classmethod
    def create_embedding(cls, content: str) -> List[float]:
        """
        텍스트를 임베딩 벡터로 변환합니다.
        
        Args:
            content: 임베딩할 텍스트
        
        Returns:
            임베딩 벡터 (리스트)
        """
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
        client = genai.Client(api_key=api_key)
        
        embedding_result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=content
        )
        
        # 응답 구조 확인 및 임베딩 추출
        if hasattr(embedding_result, 'embeddings'):
            if len(embedding_result.embeddings) > 0:
                return list(embedding_result.embeddings[0].values)
            else:
                raise ValueError("임베딩이 비어있습니다")
        elif isinstance(embedding_result, dict):
            if 'embedding' in embedding_result:
                return embedding_result['embedding']
            elif 'embeddings' in embedding_result and len(embedding_result['embeddings']) > 0:
                return embedding_result['embeddings'][0].get('values', [])
            elif 'values' in embedding_result:
                return embedding_result['values']
            else:
                raise ValueError(f"예상치 못한 응답 구조: {embedding_result.keys()}")
        elif hasattr(embedding_result, 'embedding'):
            return embedding_result.embedding
        elif hasattr(embedding_result, 'values'):
            return list(embedding_result.values) if not isinstance(embedding_result.values, list) else embedding_result.values
        else:
            raise ValueError(f"임베딩 추출 실패 - 응답 타입: {type(embedding_result)}")
    
    @classmethod
    def summarize_precedent_langchain(cls, precedent_content: str) -> str:
        """
        LangChain을 사용하여 판례를 요약하고 주요 쟁점을 추출합니다.
        """
        llm = cls.get_llm()

        # 1. 고도화된 법률 프롬프트 템플릿 정의
        template = """
        당신은 대한민국 대법원 판결문을 분석하고 요약하는 전문 법률 상담가입니다. 
        제공된 판례 전문을 바탕으로 다음 지침에 따라 분석 결과를 작성하세요.

        [지침]
        1. 사건 요약: 판례의 핵심 내용, 판결 결과, 주요 판단 근거를 포함하여 '반드시 2~3줄'로 작성하세요.
        2. 주요 쟁점: 이 사건에서 법적으로 다투어진 핵심 이슈와 법원의 판단 기준을 '반드시 3~4줄'로 상세히 작성하세요.
        3. 어조: 전문적이고 객관적인 법률 용어를 사용하세요.
        4. 형식: 아래의 구분선을 사용하여 출력하세요.

        ---
        - 사건 요약
        (내용 작성)

        - 주요 쟁점
        (내용 작성)
        ---

        [판례 전문]
        {precedent_content}
        """

        prompt = PromptTemplate.from_template(template)

        # 2. LangChain 표현식(LCEL)을 이용한 체인 구성
        chain = prompt | llm | StrOutputParser()

        try:
            # 3. 체인 실행
            response = chain.invoke({"precedent_content": precedent_content})
            return response
        except Exception as e:
            logging.error(f"LangChain 요약 중 오류 발생: {str(e)}")
            return f"요약 생성 중 오류가 발생했습니다: {str(e)[:100]}"

class OpenSearchService:
    """OpenSearch 관련 서비스 클래스"""
    
    _client: Optional[OpenSearch] = None
    
    @classmethod
    def get_client(cls) -> OpenSearch:
        """OpenSearch 클라이언트 인스턴스를 반환합니다."""
        if cls._client is None:
            cls._client = OpenSearch(
                hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
                http_conn_class=RequestsHttpConnection,
                use_ssl=False,
                verify_certs=False,
                ssl_show_warn=False,
                timeout=30,  # 연결 타임아웃 설정
                max_retries=3,  # 재시도 횟수
                retry_on_timeout=True,  # 타임아웃 시 재시도
            )
        return cls._client
    
    @classmethod
    def check_connection(cls) -> bool:
        """OpenSearch 서버 연결 상태를 확인합니다."""
        try:
            client = cls.get_client()
            return client.ping()
        except Exception:
            return False
    
    @classmethod
    def search_similar_precedents(
        cls,
        query_embedding: List[float],
        k: int = 4,
        size: int = 50  # 중복 제거를 위해 충분히 큰 값으로 설정
    ) -> List[Dict[str, Any]]:
        """
        임베딩 벡터를 사용하여 유사한 판례를 검색합니다.
        중복 제거 후에도 최소 k개의 판례를 반환하도록 보장합니다.
        
        Args:
            query_embedding: 검색 쿼리 임베딩 벡터
            k: 반환할 판례 개수 (최소값)
            size: 초기 검색 결과 크기
        
        Returns:
            검색된 판례 리스트 (최소 k개)
        """
        client = cls.get_client()
        
        if not client.ping():
            raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")
        
        # 중복 제거를 고려하여 size를 충분히 크게 설정
        # k개 판례를 얻기 위해 최소 k * 10 ~ k * 20 정도의 청크가 필요할 수 있음
        actual_size = max(size, k * 20)
        max_attempts = 3  # 최대 3번까지 재시도
        attempt = 0
        
        unique_precedents = {}
        
        while len(unique_precedents) < k and attempt < max_attempts:
            # 이전 시도에서 이미 가져온 결과가 있으면 더 많은 결과를 가져옴
            if attempt > 0:
                actual_size = actual_size * 2  # 이전보다 2배 더 가져오기
            
            knn_query = {
                "size": actual_size,
                "_source": {
                    "excludes": ["content_embedding"]  # 임베딩 벡터는 제외
                },
                "query": {
                    "knn": {
                        "content_embedding": {
                            "vector": query_embedding,
                            "k": actual_size  # k-NN 검색에서도 충분한 수를 가져옴
                        }
                    }
                }
            }
            
            try:
                response = client.search(
                    index=CHUNKED_INDEX_NAME,
                    body=knn_query
                )
            except NotFoundError:
                raise NotFoundError(f"인덱스 '{CHUNKED_INDEX_NAME}'를 찾을 수 없습니다. 먼저 데이터 색인을 진행해주세요.")
            
            # 결과 처리 (중복 판례 제거 및 점수가 가장 높은 청크 선택)
            for hit in response['hits']['hits']:
                score = hit['_score']
                source = hit['_source']
                precedent_id = source.get('판례일련번호')
                
                if not precedent_id:
                    continue
                
                # 이미 있는 판례면 점수가 더 높을 때만 업데이트
                if precedent_id not in unique_precedents or score > unique_precedents[precedent_id]['similarity_score']:
                    unique_precedents[precedent_id] = {
                        "id": precedent_id,
                        "case_number": source.get("caseNo", ""),
                        "case_title": source.get("caseTitle", ""),
                        "law_category": source.get("사건종류명", ""),
                        "law_subcategory": source.get("instance_name", ""),
                        "court": source.get("courtNm", ""),
                        "judgment_date": source.get("judmnAdjuDe", ""),
                        "similarity_score": score,
                        "preview": source.get("summ_contxt", ""),
                    }
            
            # 충분한 판례를 찾았으면 종료
            if len(unique_precedents) >= k:
                break
            
            attempt += 1
        
        # 유사도 점수 기준으로 내림차순 정렬
        sorted_results = sorted(
            unique_precedents.values(),
            key=lambda x: x['similarity_score'],
            reverse=True
        )
        
        # 최종 k개 선택 (가능한 만큼)
        return sorted_results[:k]
    
    
    @classmethod
    def get_precedent_by_case_number(cls, case_no: str) -> Optional[Dict[str, Any]]:
        """
        사건번호로 전체 판례 전문을 조회합니다.
        
        Args:
            case_no: 사건번호
        
        Returns:
            판례 문서 딕셔너리 또는 None
        """
        client = cls.get_client()
        
        if not client.ping():
            raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")
        
        try:
            response = client.get(
                index=PRECEDENTS_INDEX_NAME,
                id=case_no
            )
            return response['_source']
        except NotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"판례 조회 중 오류 발생: {str(e)}")