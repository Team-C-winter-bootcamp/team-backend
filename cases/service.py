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
GEMINI_MODEL = os.environ.get("GEMINI_MODEL")

if not GEMINI_MODEL:
    raise ValueError("GEMINI_MODEL 환경 변수가 설정되지 않았습니다.")


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

    @classmethod
    def analyze_case_deeply(cls, user_situation: Dict[str, Any], content_text: str) -> Dict[str, Any]:

        llm = cls.get_llm(temperature=0.2)

        situation_text = f"""
            - 누구와: {user_situation.get('who', '')}
            - 언제: {user_situation.get('when', '')}
            - 무슨 일이: {user_situation.get('what', '')}
            - 원하는 결과: {user_situation.get('want', '')}
            - 상세 내용: {user_situation.get('detail', '')}
            """

        # 판례 전문 (컨텍스트 길이를 고려하여 15,000자까지 활용)
        formatted_precedent = f"[참고 판례 전문]\n{content_text[:15000]}"

        # 프롬프트 구성
        template = """당신은 대한민국 법률 전문가입니다. [참고 판례]를 바탕으로 [사용자 상황]을 분석하여 조언을 제공하세요.

            [사용자 상황]
            {situation_text}

            {formatted_precedent}

            [분석 지침]
            1. 결과 예측: 승소 확률은 0~100 사이 숫자로 제공하고 현실적인 예측을 하세요.
            2. 행동 지침: 단계별 액션 플랜을 최소 3개 이상 제시하세요.
            3. 증거 전략: 필수 증거와 권장 증거를 구분하여 수집 팁을 제공하세요.
            4. 법적 근거: 적용되는 법률 조항을 명시하세요.

            반드시 다음 JSON 형식으로만 응답하세요:
            {{
              "outcome_prediction": {{
                "win_probability": 0-100,
                "expected_compensation": "문자열",
                "estimated_duration": "문자열",
                "risk_factors": ["위험요소"],
                "confidence_level": "높음/보통/낮음"
              }},
              "action_roadmap": {{
                "steps": [
                  {{ "step_number": 1, "title": "제목", "description": "설명", "priority": "필수/권장", "estimated_time": "시간" }}
                ],
                "summary": "요약"
              }},
              "evidence_strategy": {{
                "required_evidence": [{{ "name": "명칭", "type": "REQUIRED", "description": "설명", "collection_tips": "팁" }}],
                "recommended_evidence": [{{ "name": "명칭", "type": "RECOMMENDED", "description": "설명", "collection_tips": "팁" }}],
                "general_tips": "가이드"
              }},
              "legal_foundation": {{
                "applicable_laws": ["조항"],
                "legal_principles": ["원칙"],
                "relevant_precedents": [{{ "case_number": "번호", "case_title": "제목", "relevance": "관련성", "key_points": ["포인트"] }}]
              }}
            }}"""

        prompt = ChatPromptTemplate.from_template(template)
        json_parser = JsonOutputParser()

        # 체인 실행 (에러 처리는 호출부인 View에서 수행하도록 try-except 제거)
        chain = prompt | llm | json_parser

        response = chain.invoke({
            "situation_text": situation_text,
            "formatted_precedent": formatted_precedent
        })

        return response



class OpenSearchService:
    _client: Optional[OpenSearch] = None

    @classmethod
    def get_client(cls) -> OpenSearch:
        if cls._client is None:
            cls._client = OpenSearch(
                hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
                http_conn_class=RequestsHttpConnection,
                use_ssl=False,
                verify_certs=False,
                ssl_show_warn=False,
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
                    "id": source.get("id"),  # 사건번호 (caseNo)
                    "caseNm": source.get("caseNm"),  # 사건명
                    "title": source.get("title"),  # 판례 제목
                    "category": source.get("category"),  # 대분류 (민사/형사 등)
                    "subcategory": source.get("subcategory"),  # 소분류 (배임/해임 등)
                    "court": source.get("court"),  # 법원명
                    "date": source.get("date"),  # 선고일자
                    "score": hit['_score'],  # 유사도 점수 (OpenSearch가 계산)
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
