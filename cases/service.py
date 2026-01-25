import os
import logging
from typing import List, Dict, Optional, Any

# LangChain 관련 임포트
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from typing import List as TypingList
import json

# OpenSearch 관련 임포트
from opensearchpy import OpenSearch, RequestsHttpConnection, NotFoundError
import google.genai as genai

# 설정 상수
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 9200))

EMBEDDING_MODEL = "models/text-embedding-004"
GEMINI_MODEL = "gemini-3-flash-preview"

if not GEMINI_MODEL:
    raise ValueError("GEMINI_MODEL 환경 변수가 설정되지 않았습니다.")


class GeminiService:
    _llm: Optional[ChatGoogleGenerativeAI] = None

    @classmethod
    def get_llm(cls, temperature: float = 0.2) -> ChatGoogleGenerativeAI:
        if cls._llm is None:
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

            # 모델명 정규화: models/ 접두사 제거 및 공백 제거
            model_name = GEMINI_MODEL.replace("models/", "").strip()

            # LangChain ChatGoogleGenerativeAI는 모델명만 필요 (models/ 접두사 없음)
            cls._llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=api_key,
                temperature=temperature,
                max_output_tokens=4096, # 구조화된 JSON 응답을 위해 충분한 토큰 확보
                top_p=0.95,
            )
        return cls._llm

    @classmethod
    def create_embedding(cls, content: str) -> List[float]:

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")

        client = genai.Client(api_key=api_key)

        embedding_result = client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=content
        )

        # 응답 구조 확인 및 임베딩 추출
        if not embedding_result.embeddings:
            raise ValueError("임베딩 결과를 찾을 수 없습니다.")

        return embedding_result.embeddings[0].values

    @classmethod
    def summarize_precedent_langchain(cls, precedent_content: str) -> str:
        llm = cls.get_llm()

        template = """
        당신은 대한민국 대법원 판결문 분석 전문가입니다.

        [작성 지침]
        1. 모든 강조 기호(**)를 제거하고, 인사말 없이 본론만 작성하세요.
        2. 결과 요약: 기호 '■'를 사용하지 말고, 내용은 한 문단으로 간결하게 작성하세요.
        3. 사실관계: 기호 '·'를 사용하지 말고, 줄바꿈 횟수를 최소화하되 가독성을 위해 문장 시작 시 공백 2칸을 넣으세요.
        4. 불필요한 빈 줄(Blank line)을 생성하지 마세요.

        [형식]
        결과 요약
        ■ --- 사건 요약 - 주요 쟁점 ---

        사실관계
        ·   첫 번째 사실관계 내용입니다.
        ·   두 번째 사실관계 내용입니다.

        [판례 전문]
        {precedent_content}
        """

        prompt = PromptTemplate.from_template(template)
        chain = prompt | llm | StrOutputParser()

        return chain.invoke({"precedent_content": precedent_content})

    @classmethod
    def analyze_case_deeply(cls, user_situation: Dict[str, Any], content_text: str) -> Dict[str, Any]:
        llm = cls.get_llm(temperature=0.2)

        situation_str = f"대상: {user_situation.get('who', '')} / 사건: {user_situation.get('what', '')}\n상세: {user_situation.get('detail', '')}"
        precedent_str = content_text[:10000]

        template = """당신은 대한민국 법률 전문가입니다.

        [사용자 상황]
        {situation_text}

        [참고 판례 전문]
        {formatted_precedent}

        위 두 데이터를 정밀하게 비교하여 분석 보고서를 작성하세요. 
        특히 'radar_data'의 점수는 다음 기준에 따라 동적으로 산출하세요:
        - A (내 사건): 사용자 상황에서 나타나는 각 요소의 강도 (0~100)
        - B (판례): 참고한 판례에서 인정된 각 요소의 강도 (0~100)

        {{
          "outcome_prediction": {{
            "probability": "0~100 사이의 숫자로 계산된 승소/유죄 가능성",
            "expected_result": "판례와 비교했을 때 예상되는 결과",
            "expected_compensation": "예상 합의금 또는 배상액 범위",
            "estimated_duration": "예상 절차 소요 기간",
            "sentence_distribution": [
              {{ "name": "벌금형", "value": "상황에 따른 확률(%)" }},
              {{ "name": "집행유예", "value": "상황에 따른 확률(%)" }},
              {{ "name": "실형", "value": "상황에 따른 확률(%)" }}
            ],
            "radar_data": [
              {{ "subject": "고의성", "A": "사용자 상황의 고의성 정도", "B": "판례의 고의성 인정 정도", "fullMark": 100 }},
              {{ "subject": "피해규모", "A": "사용자 상황의 피해액/피해정도", "B": "판례의 피해액/피해정도", "fullMark": 100 }},
              {{ "subject": "증거확보", "A": "사용자가 확보한 증거의 객관성", "B": "판례에서 사용된 증거 수준", "fullMark": 100 }},
              {{ "subject": "합의여부", "A": "현재 사용자의 합의 진행도", "B": "판례 당시의 합의 여부", "fullMark": 100 }},
              {{ "subject": "법리복잡성", "A": "상황의 법적 다툼 여지", "B": "판례의 법리적 난이도", "fullMark": 100 }}
            ],
            "compensation_distribution": [
              {{ "range": "100-300", "count": "유사 사례 빈도수", "is_target": "해당 구간 여부(true/false)" }},
              {{ "range": "300-500", "count": "유사 사례 빈도수", "is_target": "해당 구간 여부(true/false)" }},
              {{ "range": "500-700", "count": "유사 사례 빈도수", "is_target": "해당 구간 여부(true/false)" }},
              {{ "range": "700+", "count": "유사 사례 빈도수", "is_target": "해당 구간 여부(true/false)" }}
            ]
          }},
          "action_roadmap": [
            {{ "title": "1단계 전략", "description": "가장 먼저 해야 할 법적 조치" }},
            {{ "title": "2단계 전략", "description": "중기적 대응 및 증거 보완" }},
            {{ "title": "3단계 전략", "description": "최종 마무리 및 합의/재판 전략" }}
          ],
          "legal_foundation": {{
            "logic": "판례와 사용자 상황의 핵심 차이점 및 유리한 점 요약",
            "relevant_precedents": [
              {{ "case_number": "판례번호", "key_points": ["이 사건에 적용할 핵심 이유"] }}
            ]
          }}
        }}"""

        prompt = ChatPromptTemplate.from_template(template)
        chain = prompt | llm | JsonOutputParser()

        return chain.invoke({
            "situation_text": situation_str,
            "formatted_precedent": precedent_str
        })



# service.py 내 OpenSearchService 클래스 부분
class OpenSearchService:
    _client: Optional[OpenSearch] = None

    @classmethod
    def get_client(cls) -> OpenSearch:
        if cls._client is None:
            # 환경 변수에서 호스트를 가져오되, 없으면 'localhost'를 기본값으로 사용
            host = os.environ.get("OPENSEARCH_HOST", "localhost") 
            port = int(os.environ.get("OPENSEARCH_PORT", 9200))
            
            cls._client = OpenSearch(
                hosts=[{'host': host, 'port': port}],
                http_conn_class=RequestsHttpConnection,
                use_ssl=False,
                verify_certs=False,
                # 연결 재시도 설정 추가 (서버가 뜰 때까지 대기)
                retry_on_timeout=True,
                max_retries=3
            )
        return cls._client

    @classmethod
    def check_connection(cls) -> bool:
        try:
            client = cls.get_client()
            return client.ping()
        except Exception:
            return False

    @classmethod
    # k = 최대 response할 판례문 개수
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
                source = hit['_source']  # OpenSearch에서 가져온 원본 데이터
                unique_precedents[p_id] = {
                    "case_No": source.get("id"),  # 사건번호 (caseNo)
                    "case_name": source.get("caseNm"),  # 사건명
                    "case_title": source.get("title"),  # 판례 제목
                    "law_category": source.get("category"),  # 대분류 (민사/형사 등)
                    "law_subcategory": source.get("subcategory"),  # 소분류 (배임/해임 등)
                    "court": source.get("court"),  # 법원명
                    "judgment_date": source.get("date"),  # 선고일자
                    "similarity": hit['_score'],  # 유사도 점수 (OpenSearch가 계산)
                    "preview": source.get("preview")
                }
            if len(unique_precedents) >= k: break  # k개 채우면 즉시 종료

        return list(unique_precedents.values())


    @classmethod
    def get_precedent_by_case_number(cls, case_no: str) -> Optional[Dict[str, Any]]:
        client = cls.get_client()

        if not client.ping():
            raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")

        try:
            response = client.get(
                index="precedents",
                id=case_no
            )
            return response['_source']
        except NotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"판례 조회 중 오류 발생: {str(e)}")
