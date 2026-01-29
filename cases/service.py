import os
import logging
from typing import List, Dict, Optional, Any

# LangChain 관련 임포트
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import json

# OpenSearch 관련 임포트
from opensearchpy import OpenSearch, NotFoundError
import google.genai as genai

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 환경 변수 로드
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 443))
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME")
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD")

# OpenSearch precedents_chunked 인덱스와 통일 (gemini-embedding-001 기본 3072 → output_dimensionality로 768 사용)
EMBEDDING_MODEL_NAME = "gemini-embedding-001"
EMBEDDING_DIMENSION = 768


class GeminiService:
    _llm: Optional[ChatGoogleGenerativeAI] = None

    @staticmethod
    def _clean_model_name(model_name: str) -> str:
        """SDK 오류 방지를 위해 'models/' 접두사 제거 및 공백 정제"""
        if not model_name:
            return ""
        # 'models/gemini-embedding-001' -> 'gemini-embedding-001'
        cleaned = model_name.strip().split("/")[-1]
        return cleaned

    @classmethod
    def get_llm(cls, temperature: float = 0.0) -> ChatGoogleGenerativeAI:
        if cls._llm is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

            # 환경변수에서 실시간으로 모델명을 읽어와 정제
            raw_gemini_model = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
            model = cls._clean_model_name(raw_gemini_model)
            
            cls._llm = ChatGoogleGenerativeAI(
                model=model,
                google_api_key=api_key,
                temperature=temperature,
                max_output_tokens=4096,
                top_p=0.95,
            )
        return cls._llm

    @classmethod
    def create_embedding(cls, content: str, is_query: bool = True) -> List[float]:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")
            
        client = genai.Client(api_key=api_key)
        model = cls._clean_model_name(EMBEDDING_MODEL_NAME)
        task_type = "RETRIEVAL_QUERY" if is_query else "RETRIEVAL_DOCUMENT"
        # gemini-embedding-001 기본 출력은 3072차원. OpenSearch 인덱스에 맞추기 위해 output_dimensionality 명시
        config = {"task_type": task_type, "output_dimensionality": EMBEDDING_DIMENSION}

        try:
            embedding_result = client.models.embed_content(
                model=model,
                contents=content,
                config=config
            )
        except Exception as e:
            logging.error(f"Embedding API Error (Model: {model}): {str(e)}")
            raise e

        if not embedding_result.embeddings:
            raise ValueError("임베딩 결과를 찾을 수 없습니다.")

        return embedding_result.embeddings[0].values

    @classmethod
    def summarize_precedent_langchain(cls, precedent_content: str) -> dict:
        llm = cls.get_llm()
        
        template = """
        당신은 판결문의 핵심 법리와 결과를 통찰력 있게 분석하는 법률 전문가입니다.
        반드시 지정된 JSON 형식으로만 답변하세요.

        [작성 지침]
        1. core_summary: '어떤 법적 쟁점에 대해 법원이 어떤 이유로 결론을 내렸는지'를 포함하여 임팩트 있는 한 문장으로 작성하십시오.
        2. key_fact: 사건의 핵심 발단이 된 사실관계를 1가지만 짧게 작성하십시오.
        3. verdict: 최종 판결 상태(예: 유죄 확정, 상고 기각, 파기환송 등)를 명확히 적으십시오.
        4. legal_point: 법원의 판단 근거가 된 핵심 법리나 조항을 적으십시오.
        5. tags: 사건과 관련된 핵심 키워드 3개를 리스트 형태로 작성하십시오.

        [형식]
        {{
            "core_summary": "쟁점과 결론이 포함된 통찰력 있는 요약",
            "key_fact": "사건의 핵심 발단",
            "verdict": "판결 결과",
            "legal_point": "법적 근거 및 판단 요지",
            "tags": ["키워드1", "키워드2", "키워드3"]
        }}

        [판례 전문]
        {precedent_content}
        """
        
        prompt = PromptTemplate.from_template(template)
        chain = prompt | llm | JsonOutputParser()
        return chain.invoke({"precedent_content": precedent_content})

    @classmethod
    def analyze_case_deeply(cls, user_situation: Dict[str, Any], content_text: str) -> Dict[str, Any]:
        llm = cls.get_llm()
        
        situation_str = (
            f"대상: {user_situation.get('who', '')} / "
            f"사건: {user_situation.get('what', '')}\n"
            f"상세 내용: {user_situation.get('detail', '')}\n"
            f"요구사항: {user_situation.get('want', '법적 조언')}"
        )
        precedent_str = content_text[:10000]

        template = """당신은 대한민국 법률 전문가입니다. 사용자의 상황과 참고 판례를 정밀하게 비교 분석하여 보고서를 작성하세요.
    
        [사용자 상황]
        {situation_text}

        [참고 판례]
        {formatted_precedent}

        반드시 아래의 JSON 구조를 엄격히 지켜 답변하십시오:

        {{
          "outcome_prediction": {{
            "probability": "0~100 사이의 승소/유죄 가능성 숫자",
            "expected_result": "판례와 비교했을 때 예상되는 최종 결과",
            "expected_compensation": "예상되는 합의금 또는 배상액의 구체적 범위",
            "estimated_duration": "절차 소요 예상 기간 (예: 6개월~1년)",
            "sentence_distribution": [
              {{ "name": "벌금형", "value": "확률(%)" }},
              {{ "name": "집행유예", "value": "확률(%)" }},
              {{ "name": "실형", "value": "확률(%)" }}
            ],
            "radar_data": [
              {{ "subject": "고의성", "A": "사용자 상황 점수(0-100)", "B": "판례 인정 점수(0-100)", "fullMark": 100 }},
              {{ "subject": "피해규모", "A": "사용자 상황 점수", "B": "판례 인정 점수", "fullMark": 100 }},
              {{ "subject": "증거확보", "A": "사용자 상황 점수", "B": "판례 인정 점수", "fullMark": 100 }},
              {{ "subject": "합의여부", "A": "사용자 상황 점수", "B": "판례 인정 점수", "fullMark": 100 }},
              {{ "subject": "법리복잡성", "A": "사용자 상황 점수", "B": "판례 인정 점수", "fullMark": 100 }}
            ],
            "compensation_distribution": [
              {{ "range": "하위 25%", "count": "빈도", "is_target": false }},
              {{ "range": "중간값", "count": "빈도", "is_target": true }},
              {{ "range": "상위 25%", "count": "빈도", "is_target": false }}
            ]
          }},
          "action_roadmap": [
            {{ "title": "단기 전략", "description": "즉시 실행해야 할 법적 조치" }},
            {{ "title": "중기 전략", "description": "증거 보완 및 대응 방안" }},
            {{ "title": "장기 전략", "description": "재판/합의 마무리 전략" }}
          ],
          "legal_foundation": {{
            "logic": "판례와 사용자 상황의 핵심 차이점 및 유리한 법리 요약",
            "relevant_precedents": [
              {{ "case_number": "판례번호", "key_points": ["적용 근거 리스트"] }}
            ]
          }}
        }}"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm | JsonOutputParser()

        return chain.invoke({
            "situation_text": situation_str,
            "formatted_precedent": precedent_str
        })

class OpenSearchService:
    _client: Optional[OpenSearch] = None

    @classmethod
    def get_client(cls) -> OpenSearch:
        if cls._client is None:
            cls._client = OpenSearch(
                hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
                http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
                use_ssl=True,
                verify_certs=True,
                retry_on_timeout=True,
                max_retries=3,
            )
        return cls._client

    @classmethod
    def check_connection(cls) -> bool:
        try:
            return cls.get_client().ping()
        except Exception:
            return False

    @classmethod
    def search_similar_precedents(cls, query_embedding: List[float], k: int = 5) -> List[Dict[str, Any]]:
        client = cls.get_client()
        knn_query = {
            "size": 50,
            "_source": {"excludes": ["content_embedding"]},
            "query": {"knn": {"content_embedding": {"vector": query_embedding, "k": 50}}}
        }
        
        response = client.search(index="precedents_chunked", body=knn_query)
        unique_precedents = {}
        
        for hit in response['hits']['hits']:
            source = hit['_source']
            p_id = source.get('id')
            if p_id and p_id not in unique_precedents:
                unique_precedents[p_id] = {
                    "case_No": source.get("id"),
                    "case_name": source.get("caseNm"),
                    "case_title": source.get("title"),
                    "law_category": source.get("category"),
                    "law_subcategory": source.get("subcategory"),
                    "court": source.get("court"),
                    "judgment_date": source.get("date"),
                    "similarity": hit['_score'],
                    "preview": source.get("preview")
                }
            if len(unique_precedents) >= k: break
        return list(unique_precedents.values())

    @classmethod
    def get_precedent_by_case_number(cls, case_no: str) -> Optional[Dict[str, Any]]:
        client = cls.get_client()
        try:
            response = client.get(index="precedents", id=case_no)
            return response['_source']
        except NotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"판례 조회 중 오류 발생: {str(e)}")
