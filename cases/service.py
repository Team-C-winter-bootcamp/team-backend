import os
import logging
from typing import List, Dict, Optional, Any

# LangChain 관련 임포트
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from typing import List as TypingList
import json

# Pydantic 모델을 위한 임포트 (검증용)
try:
    from pydantic import BaseModel, Field
except ImportError:
    # Pydantic이 없으면 기본 dict만 사용
    BaseModel = None
    Field = None

# OpenSearch 관련 임포트
from opensearchpy import OpenSearch, RequestsHttpConnection, NotFoundError
import google.genai as genai

# 설정 상수
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 9200))
CHUNKED_INDEX_NAME = "precedents_chunked"
PRECEDENTS_INDEX_NAME = "precedents"
EMBEDDING_MODEL = "models/text-embedding-004"
GEMINI_MODEL = os.environ.get("GEMINI_MODEL")
if not GEMINI_MODEL:
    raise ValueError("GEMINI_MODEL 환경 변수가 설정되지 않았습니다.")

# --- JSON 스키마 정의 (구조화된 출력을 위한 참고용) ---
# Pydantic 모델 대신 JSON 스키마를 프롬프트에 포함하여 구조화된 응답을 유도합니다.

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
    

    
    @classmethod
    def generate_answer_from_precedents(cls, precedent_contents: List[str]) -> Dict[str, Any]:
        """
        제공된 판례 본문 목록을 바탕으로 구조화된 답변을 생성합니다.
        """
        llm = cls.get_llm(temperature=0.3)

        # 프롬프트에 전달할 판례 본문들을 하나로 합칩니다.
        full_text = "\n\n---\n\n".join(precedent_contents)

        template = """
        당신은 대한민국 최고 법률 AI입니다. 제공되는 여러 판례 전문을 종합적으로 분석하여, 사용자의 잠재적 법률 문제에 대한 실행 가능한 솔루션을 구조화된 JSON 형식으로 제공해야 합니다.

        [분석 대상 판례 전문]
        {full_text}

        [분석 및 답변 생성 지침]
        1.  **종합 분석**: 개별 판례가 아닌, 모든 판례의 내용을 종합하여 핵심 쟁점과 법리를 관통하는 일관된 분석을 제공하세요.
        2.  **실행 중심**: 사용자가 실제로 취할 수 있는 구체적인 행동과 전략을 중심으로 답변을 구성하세요.
        3.  **구조 준수**: 반드시 아래에 명시된 JSON 형식과 키 이름을 정확히 지켜서 응답해야 합니다. 다른 어떤 텍스트도 추가하지 마세요.

        [필수 출력 JSON 형식]
        {{
          "outcome_prediction": {{
            "probability": "예상 승소 또는 합의 가능성 (예: '75% 이상')",
            "expected_result": "가장 가능성 있는 결과에 대한 요약 (예: '임대인의 수리 의무 인정 및 손해배상 책임 발생')",
            "estimated_compensation": "예상되는 배상 또는 보상 금액 범위 (예: '약 150만원 ~ 250만원')",
            "estimated_duration": "문제 해결까지 예상되는 소요 기간 (예: '내용증명 발송 후 1~2개월 내 합의 가능')"
          }},
          "action_roadmap": [
            {{
              "step": 1,
              "title": "첫 번째 조치의 제목 (예: '손해 사실 공식 통보 및 증거 확보')",
              "action": "실행할 구체적인 행동 (예: '누수 관련 내용증명 발송')",
              "description": "해당 조치의 목적과 방법에 대한 상세 설명"
            }},
            {{
              "step": 2,
              "title": "두 번째 조치의 제목 (예: '객관적인 손해 비용 산정')",
              "action": "실행할 구체적인 행동 (예: '전문 수리업체로부터 복수 견적서 확보')",
              "description": "해당 조치의 목적과 방법에 대한 상세 설명"
            }}
          ],
          "evidence_strategy": {{
            "status": "현재 필요한 증거 확보 상태 (예: '필수 증거 확보 시급')",
            "checklist": [
              {{
                "item": "확보해야 할 증거 항목 (예: '누수 부위 및 피해 상황을 담은 사진/영상')",
                "status": "증거의 중요도 (예: 'REQUIRED' 또는 'RECOMMENDED')",
                "tip": "증거 확보 시 유의사항 및 팁 (예: '촬영 날짜와 시간이 나오도록 설정 후 촬영')"
              }},
              {{
                "item": "확보해야 할 증거 항목 (예: '임대인과의 수리 요구 관련 대화 기록')",
                "status": "증거의 중요도 (예: 'REQUIRED')",
                "tip": "증거 확보 시 유의사항 및 팁 (예: '문자, 카카오톡 메시지, 통화 녹음 등')"
              }}
            ]
          }},
          "legal_foundation": {{
            "logic": "분석의 핵심이 되는 법적 논리 (예: '민법 제623조에 따라, 임대인은 계약 존속 중 임차인이 목적물을 사용·수익하는데 필요한 상태를 유지하게 할 의무를 부담한다.')",
            "precedent_ref": "분석의 근거가 된 주요 판례 번호 및 핵심 판시사항 요약 (예: '대법원 201X다XXXX 판결: 임대인 수선의무는 특약에 의해 면제할 수 있으나, 대규모 수선은 여전히 임대인이 부담한다.')"
          }}
        }}
        """

        prompt = PromptTemplate.from_template(template)
        json_parser = JsonOutputParser()
        chain = prompt | llm | json_parser

        try:
            response = chain.invoke({"full_text": full_text})
            if isinstance(response, dict):
                processed_response = cls._post_process_gemini_answer(response)
                return processed_response
            else:
                try:
                    parsed_response = json.loads(str(response))
                    processed_response = cls._post_process_gemini_answer(parsed_response)
                    return processed_response
                except json.JSONDecodeError:
                    logging.error(f"JSON 파싱 실패: {response}")
                    return {
                        "error": "AI 답변을 생성하는 중 오류가 발생했습니다.",
                        "details": "Gemini 응답을 JSON으로 파싱할 수 없습니다."
                    }
        except Exception as e:
            logging.error(f"종합 답변 생성 중 오류 발생: {str(e)}", exc_info=True)
            # 실패 시 기본 구조 또는 오류 메시지를 담은 구조 반환
            return {
                "error": "AI 답변을 생성하는 중 오류가 발생했습니다.",
                "details": str(e)
            }
    
    @classmethod
    def _post_process_gemini_answer(cls, raw_answer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gemini AI의 응답을 후처리하여 정의된 스키마에 맞도록 보완합니다.
        누락되거나 형식에 맞지 않는 필드에 기본값을 제공하거나 필터링합니다.
        """
        processed_answer = {
            "outcome_prediction": {
                "probability": raw_answer.get("outcome_prediction", {}).get("probability", "정보 없음"),
                "expected_result": raw_answer.get("outcome_prediction", {}).get("expected_result", "정보 없음"),
                "estimated_compensation": raw_answer.get("outcome_prediction", {}).get("estimated_compensation", "정보 없음"),
                "estimated_duration": raw_answer.get("outcome_prediction", {}).get("estimated_duration", "정보 없음"),
            },
            "action_roadmap": [],  # 여기에 채워질 예정
            "evidence_strategy": {
                "status": raw_answer.get("evidence_strategy", {}).get("status", "정보 없음"),
                "checklist": []  # 여기에 채워질 예정
            },
            "legal_foundation": {
                "logic": raw_answer.get("legal_foundation", {}).get("logic", "정보 없음"),
                "precedent_ref": raw_answer.get("legal_foundation", {}).get("precedent_ref", "정보 없음"),
            }
        }

        # Process action_roadmap
        if "action_roadmap" in raw_answer and isinstance(raw_answer["action_roadmap"], list):
            for step_data in raw_answer["action_roadmap"]:
                # 필수 필드가 모두 있는지 확인
                if all(k in step_data for k in ["step", "title", "action", "description"]):
                    processed_answer["action_roadmap"].append({
                        "step": step_data.get("step", 0),
                        "title": step_data.get("title", "정보 없음"),
                        "action": step_data.get("action", "정보 없음"),
                        "description": step_data.get("description", "정보 없음"),
                    })
        
        # Process evidence_strategy.checklist
        if "evidence_strategy" in raw_answer and "checklist" in raw_answer["evidence_strategy"] \
           and isinstance(raw_answer["evidence_strategy"]["checklist"], list):
            for item_data in raw_answer["evidence_strategy"]["checklist"]:
                # 필수 필드가 모두 있는지 확인
                if all(k in item_data for k in ["item", "status", "tip"]):
                    processed_answer["evidence_strategy"]["checklist"].append({
                        "item": item_data.get("item", "정보 없음"),
                        "status": item_data.get("status", "정보 없음"),
                        "tip": item_data.get("tip", "정보 없음"),
                    })

        return processed_answer



    


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
            logging.info(f"OpenSearch client initialized with host: {OPENSEARCH_HOST} (type: {type(OPENSEARCH_HOST)}), port: {OPENSEARCH_PORT} (type: {type(OPENSEARCH_PORT)})")
        return cls._client
    
    @classmethod
    def check_connection(cls) -> bool:
        """OpenSearch 서버 연결 상태를 확인합니다."""
        try:
            client = cls.get_client()
            return client.ping()
        except Exception as e:
            logging.error(f"OpenSearch 연결 확인 중 오류 발생: {e}", exc_info=True)
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
                raise NotFoundError(f"인덱스 '{{CHUNKED_INDEX_NAME}}'를 찾을 수 없습니다. 먼저 데이터 색인을 진행해주세요.")
            
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
            raise ValueError(f"판례 조회 중 오류 발생: {{str(e)}}")

    @classmethod
    def get_precedents_by_case_numbers(cls, case_nos: List[str]) -> List[Dict[str, Any]]:
        """
        여러 사건번호로 전체 판례 전문을 한 번에 조회합니다.
        
        Args:
            case_nos: 사건번호 리스트
        
        Returns:
            판례 문서 딕셔너리 리스트
        """
        client = cls.get_client()
        
        if not client.ping():
            raise ConnectionError("OpenSearch 서버에 연결할 수 없습니다.")
        
        if not case_nos:
            return []
            
        try:
            response = client.mget(
                index=PRECEDENTS_INDEX_NAME,
                body={'ids': case_nos}
            )
            
            # 결과에서 _source만 추출하고, found가 true인 것만 필터링
            return [doc['_source'] for doc in response['docs'] if doc['found']]
        
        except NotFoundError:
             # mget은 인덱스가 없으면 404를 반환하지 않을 수 있으므로, ping으로 미리 확인.
             # 이 코드는 실행되지 않을 수 있으나 안전장치로 둠.
            return []
        except Exception as e:
            raise ValueError(f"여러 판례 조회 중 오류 발생: {{str(e)}}")