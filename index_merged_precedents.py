import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any, Generator

# 서비스 클래스 임포트
from cases.service import GeminiService, OpenSearchService
from opensearchpy import helpers
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 환경변수 로드
env_path = Path(__file__).parent / ".env.prod"
load_dotenv(dotenv_path=env_path, override=True)

# 설정 상수
CHUNKED_INDEX_NAME = "precedents_chunked"
PRECEDENTS_INDEX_NAME = "precedents"
VECTOR_DIMENSION = 768
MERGED_DATA_DIR = Path(__file__).parent / "data" / "merged"

opensearch_client = OpenSearchService.get_client()

# --- [전처리 유틸리티] 벡터 검색 노이즈 제거 ---

def parse_date(date_str: str) -> str:
    """날짜를 필터링용(yyyy-MM-dd)으로 정규화"""
    if not date_str:
        return None
    nums = re.findall(r'\d+', str(date_str))
    if len(nums) >= 3:
        return f"{nums[0]}-{nums[1].zfill(2)}-{nums[2].zfill(2)}"
    return date_str

def clean_legal_text(text: str) -> str:
    """벡터 검색에 방해되는 노이즈(태그, 이름, 사건번호 등) 제거"""
    if not text:
        return ""
    
    # 1. 특수 태그 및 헤더 제거 (예: 【판시사항】, 【판결요지】 등)
    text = re.sub(r'【.*?】', '', text)
    
    # 2. 사건번호 패턴 제거 (예: 75도1003, 2023다12345 등)
    text = re.sub(r'\d{2,4}[가-힣]{1,3}\d+', '', text)
    
    # 3. 날짜 패턴 제거 (텍스트 내의 날짜는 벡터 검색에 노이즈가 될 수 있음)
    text = re.sub(r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.', '', text)
    
    # 4. 불필요한 공백 및 줄바꿈 정리
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def smart_split(text_list: List[str]) -> List[str]:
    """텍스트 리스트를 합쳐서 의미 있는 단위로 분할"""
    # 전처리 적용 후 결합
    combined_text = "\n".join([clean_legal_text(t) for t in text_list if t])
    chunks = re.split(r'[.\n]', combined_text)
    return [c.strip() for c in chunks if len(c.strip()) > 15] # 너무 짧은 문장은 제외

# --- [인덱스 설정] ---

def create_indices():
    """인덱스 초기화 (변호인 필드 제외, 벡터 최적화)"""
    
    # 1. chunked 인덱스 (검색용)
    if opensearch_client.indices.exists(index=CHUNKED_INDEX_NAME):
        opensearch_client.indices.delete(index=CHUNKED_INDEX_NAME)

    chunked_body = {
        "settings": {"index": {"knn": True, "refresh_interval": "1s"}},
        "mappings": {
            "properties": {
                "content_embedding": {
                    "type": "knn_vector",
                    "dimension": VECTOR_DIMENSION,
                    "method": {"name": "hnsw", "space_type": "l2", "engine": "faiss"}
                },
                "id": {"type": "keyword"},
                "caseNm": {"type": "text"},
                "date": {"type": "date", "format": "yyyy-MM-dd"},
                "chunk_content": {"type": "text"} # 정제된 텍스트 저장
            }
        }
    }
    opensearch_client.indices.create(index=CHUNKED_INDEX_NAME, body=chunked_body)

    # 2. 원본 인덱스 (조회용)
    if not opensearch_client.indices.exists(index=PRECEDENTS_INDEX_NAME):
        precedents_body = {
            "mappings": {
                "properties": {
                    "case_no": {"type": "keyword"},
                    "case_title": {"type": "text"},
                    "judgment_date": {"type": "date", "format": "yyyy-MM-dd"},
                    "content": {"type": "text"}
                }
            }
        }
        opensearch_client.indices.create(index=PRECEDENTS_INDEX_NAME, body=precedents_body)

# --- [인덱싱 실행] ---

def get_indexing_actions() -> Generator[Dict[str, Any], None, None]:
    json_files = list(MERGED_DATA_DIR.glob("*.json"))
    
    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            case_no = data.get("caseNo")
            if not case_no: continue

            normalized_date = parse_date(data.get("judmnAdjuDe"))

            # [A] 'precedents' (원본 데이터 보존 - 변호인 필드는 아예 삭제)
            yield {
                "_index": PRECEDENTS_INDEX_NAME,
                "_id": str(case_no),
                "_source": {
                    "case_no": case_no,
                    "case_title": data.get("caseTitle"),
                    "judgment_date": normalized_date,
                    "content": data.get("판례내용", "")
                }
            }

            # [B] 'precedents_chunked' (벡터 검색 최적화)
            # 검색 품질을 높이기 위해 판시사항, 판결요지, 요약문만 사용
            summary_texts = [s.get("summ_contxt", "") for s in data.get("Summary", [])]
            target_raw_texts = [
                data.get("판시사항", ""),
                data.get("판결요지", ""),
                data.get("jdgmn", "")
            ] + summary_texts
            
            # 노이즈 제거 및 청크 분할
            chunks = smart_split(target_raw_texts)

            for i, chunk in enumerate(chunks):
                try:
                    # 임베딩 생성 (정제된 텍스트만 전달)
                    embedding_vector = GeminiService.create_embedding(chunk, is_query=False)
                    if embedding_vector:
                        yield {
                            "_index": CHUNKED_INDEX_NAME,
                            "_id": f"{case_no}_{i}",
                            "_source": {
                                "id": case_no,
                                "caseNm": data.get("caseNm"),
                                "date": normalized_date,
                                "chunk_content": chunk, # 노이즈 없는 깨끗한 텍스트
                                "content_embedding": embedding_vector
                            }
                        }
                except Exception as api_err:
                    logging.error(f"API 에러 ({case_no}): {api_err}")
                    continue

        except Exception as e:
            logging.error(f"파일 {file_path.name} 처리 중 에러: {e}")

def index_documents():
    logging.info("벡터 검색 최적화 인덱싱 시작...")
    success, errors = helpers.bulk(
        opensearch_client,
        get_indexing_actions(),
        chunk_size=50, # 임베딩 호출 효율을 위해 조정
        request_timeout=300,
        raise_on_error=False
    )
    logging.info(f"성공: {success}건, 에러: {len(errors) if isinstance(errors, list) else errors}건")

if __name__ == "__main__":
    create_indices()
    index_documents()
