import os
import logging
from typing import List, Dict, Optional, Any

# LangChain 관련 임포트
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
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
    
    @classmethod
    def analyze_case_deeply(
        cls,
        user_situation: Dict[str, Any],
        similar_precedents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        사용자의 상황과 유사 판례를 바탕으로 구조화된 심층 분석을 수행합니다.
        Pydantic 모델과 LangChain의 구조화된 출력 기능을 사용하여 더 정확하고 일관된 응답을 생성합니다.
        
        Args:
            user_situation: 사용자 상황 정보 (category, situation 등)
            similar_precedents: 유사 판례 리스트
        
        Returns:
            구조화된 분석 결과 딕셔너리
        """
        llm = cls.get_llm(temperature=0.2)
        
        # 사용자 상황 텍스트 구성
        category = user_situation.get("category", "")
        situation = user_situation.get("situation", {})
        situation_text = "\n".join([f"- {key}: {value}" for key, value in situation.items()])
        
        # 유사 판례 정보 구성
        precedents_text = ""
        for i, prec in enumerate(similar_precedents[:4], 1):  # 최대 4개만 사용
            precedents_text += f"""
판례 {i}:
- 사건번호: {prec.get('case_number', '')}
- 사건명: {prec.get('case_title', '')}
- 법원: {prec.get('court', '')}
- 판결일: {prec.get('judgment_date', '')}
- 요약: {prec.get('preview', '')}
"""
        
        # 구조화된 프롬프트 템플릿 (JSON 형식 명시)
        template = """당신은 대한민국 법률 전문가입니다. 사용자의 법률 문제를 분석하여 구조화된 조언을 제공해야 합니다.

[사용자 상황]
카테고리: {category}
상황 설명:
{situation_text}

[참고 판례]
{precedents_text}

[분석 지침]
1. 결과 예측: 승소 확률은 0~100 사이의 숫자로 제공하고, 실제 판례와 유사한 사례를 참고하여 현실적인 예측을 하세요.
2. 행동 지침: 내용증명 발송부터 합의까지 단계별로 구체적인 액션 플랜을 제시하세요. 최소 3개 이상의 단계를 포함하세요.
3. 증거 전략: 필수 증거와 권장 증거를 명확히 구분하고, 각 증거에 대한 수집 팁을 구체적으로 제공하세요.
4. 법적 근거: 적용되는 법률 조항을 정확히 명시하고, 참고 판례와의 관련성을 상세히 설명하세요.

[출력 형식]
반드시 다음 JSON 형식으로 정확히 응답하세요. 유효한 JSON만 출력하고, 추가 설명은 포함하지 마세요:

{{
  "outcome_prediction": {{
    "win_probability": 0-100 사이의 숫자,
    "expected_compensation": "예상 보상액 (예: '500만원 ~ 1000만원')",
    "estimated_duration": "예상 소요 기간 (예: '3개월 ~ 6개월')",
    "risk_factors": ["위험 요소 1", "위험 요소 2"],
    "confidence_level": "높음 또는 보통 또는 낮음"
  }},
  "action_roadmap": {{
    "steps": [
      {{
        "step_number": 1,
        "title": "단계 제목",
        "description": "단계 설명",
        "priority": "필수 또는 권장",
        "estimated_time": "예상 소요 시간"
      }}
    ],
    "summary": "전체 로드맵 요약"
  }},
  "evidence_strategy": {{
    "required_evidence": [
      {{
        "name": "증거명",
        "type": "REQUIRED",
        "description": "증거 설명",
        "collection_tips": "수집 팁"
      }}
    ],
    "recommended_evidence": [
      {{
        "name": "증거명",
        "type": "RECOMMENDED",
        "description": "증거 설명",
        "collection_tips": "수집 팁"
      }}
    ],
    "general_tips": "일반적인 증거 수집 가이드"
  }},
  "legal_foundation": {{
    "applicable_laws": ["민법 제570조", "민법 제571조"],
    "legal_principles": ["법적 원칙 설명 1", "법적 원칙 설명 2"],
    "relevant_precedents": [    
      {{
        "case_number": "사건번호",
        "case_title": "사건명",
        "relevance": "관련성 설명",
        "key_points": ["핵심 포인트 1", "핵심 포인트 2"]
      }}
    ]
  }}
}}"""
        
        prompt = PromptTemplate.from_template(template)
        
        # JsonOutputParser 사용 (summarize_precedent_langchain과 동일한 방식)
        json_parser = JsonOutputParser()
        
        # 체인 구성: 프롬프트 + LLM + JSON 파서
        chain = prompt | llm | json_parser
        
        try:
            # 체인 실행
            response = chain.invoke({
                "category": category,
                "situation_text": situation_text,
                "precedents_text": precedents_text
            })
            
            # 응답이 딕셔너리인지 확인
            if isinstance(response, dict):
                # 기본 구조 검증 및 보완
                return cls._validate_and_complete_analysis(response)
            else:
                # 문자열로 반환된 경우 JSON 파싱 시도
                try:
                    parsed = json.loads(str(response))
                    return cls._validate_and_complete_analysis(parsed)
                except json.JSONDecodeError:
                    logging.error(f"JSON 파싱 실패: {response}")
                    return cls._get_default_analysis_structure()
                
        except Exception as e:
            logging.error(f"심층 분석 중 오류 발생: {str(e)}", exc_info=True)
            # 기본 구조 반환
            return cls._get_default_analysis_structure()



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

        # 2. 결과 처리: 사전에 넣으면서 자동 중복 제거 (먼저 나온 높은 점수가 유지되도록)
        for hit in response['hits']['hits']:
            source = hit['_source']
            p_id = source.get('id')

            # p_id는 중복 제거를 위한 기준값 (예: 사건번호 또는 판례일련번호)
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
                    "preview": source.get("preview")  # 쪼개진 본문 내용 (chunk)
                }
            if len(unique_precedents) >= k: break  # k개 채우면 즉시 종료

        return list(unique_precedents.values())
    
    
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
                index="precedents",
                id=case_no
            )
            return response['_source']
        except NotFoundError:
            return None
        except Exception as e:
            raise ValueError(f"판례 조회 중 오류 발생: {str(e)}")
