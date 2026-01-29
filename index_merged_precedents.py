import os
import json
import logging
import re
import time
from pathlib import Path
from typing import List, Dict, Any, Generator

# 서비스 클래스 임포트
from cases.service import GeminiService, OpenSearchService
from opensearchpy import helpers, RequestsHttpConnection
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 환경변수 로드
env_path = Path(__file__).parent / ".env.prod"
load_dotenv(dotenv_path=env_path, override=True)

# 설정 상수 (gemini-embedding-001 기준 768차원)
CHUNKED_INDEX_NAME = "precedents_chunked"
PRECEDENTS_INDEX_NAME = "precedents"
VECTOR_DIMENSION = 768
MERGED_DATA_DIR = Path(__file__).parent / "data" / "merged"

# OpenSearch 클라이언트 설정
opensearch_client = OpenSearchService.get_client()


def smart_split(text_list: List[str]) -> List[str]:
    combined_text = "\n".join([t for t in text_list if t])
    chunks = re.split(r'[\n.]', combined_text)
    return [c.strip() for c in chunks if len(c.strip()) > 10]


def create_indices():
    """인덱스를 삭제하고 gemini-embedding-001 규격(768차원)으로 생성"""

    # 1. precedents_chunked 인덱스 (KNN 벡터 검색용)
    if opensearch_client.indices.exists(index=CHUNKED_INDEX_NAME):
        logging.info(f"기존 인덱스 삭제: {CHUNKED_INDEX_NAME}")
        opensearch_client.indices.delete(index=CHUNKED_INDEX_NAME)

    chunked_body = {
        "settings": {
            "index": {
                "knn": True,
                "refresh_interval": "1s"
            }
        },
        "mappings": {
            "properties": {
                "content_embedding": {
                    "type": "knn_vector",
                    "dimension": VECTOR_DIMENSION,  # 768차원 설정
                    "method": {
                        "name": "hnsw",
                        "space_type": "l2",
                        "engine": "faiss"
                    }
                },
                "id": {"type": "keyword"},
                "caseNm": {"type": "text"},
                "title": {"type": "text"},
                "category": {"type": "keyword"},
                "subcategory": {"type": "keyword"},
                "court": {"type": "keyword"},
                "date": {"type": "date", "format": "yyyy-MM-dd"},
                "preview": {"type": "text"},
                "chunk_content": {"type": "text"}
            }
        }
    }
    opensearch_client.indices.create(index=CHUNKED_INDEX_NAME, body=chunked_body)
    logging.info(f"768차원 KNN 인덱스 생성 완료: {CHUNKED_INDEX_NAME}")

    # 2. precedents 인덱스 (원본 데이터용)
    if not opensearch_client.indices.exists(index=PRECEDENTS_INDEX_NAME):
        precedents_body = {
            "mappings": {
                "properties": {
                    "case_no": {"type": "keyword"},
                    "case_title": {"type": "text"},
                    "case_name": {"type": "text"},
                    "court": {"type": "keyword"},
                    "judgment_date": {"type": "date", "format": "yyyy-MM-dd"},
                    "precedent_id": {"type": "integer"},
                    "issue": {"type": "text"},
                    "content": {"type": "text"}
                }
            }
        }
        opensearch_client.indices.create(index=PRECEDENTS_INDEX_NAME, body=precedents_body)
        logging.info(f"원본 판례 인덱스 생성 완료: {PRECEDENTS_INDEX_NAME}")


def get_indexing_actions() -> Generator[Dict[str, Any], None, None]:
    json_files = list(MERGED_DATA_DIR.glob("*.json"))
    logging.info(f"총 {len(json_files)}개 파일 처리 시작")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            case_no = data.get("caseNo")
            if not case_no: continue

            # [A] 'precedents' 인덱스 데이터
            yield {
                "_index": PRECEDENTS_INDEX_NAME,
                "_id": str(case_no),
                "_source": {
                    "case_no": case_no,
                    "case_title": data.get("caseTitle"),
                    "case_name": data.get("caseNm"),
                    "court": data.get("courtNm"),
                    "judgment_date": data.get("judmnAdjuDe"),
                    "precedent_id": data.get("판례일련번호"),
                    "issue": data.get("판시사항", ""),
                    "content": data.get("판례내용", "")
                }
            }

            # [B] 'precedents_chunked' 인덱스 데이터
            summary_texts = [s.get("summ_contxt", "") for s in data.get("Summary", [])]
            target_texts = [
                               data.get("판시사항", ""),
                               data.get("판결요지", ""),
                               data.get("jdgmn", "")
                           ] + summary_texts
            chunks = smart_split(target_texts)

            for i, chunk in enumerate(chunks):
                try:
                    # GeminiService 명세(768차원 반환)에 맞춰 호출
                    embedding_vector = GeminiService.create_embedding(chunk, is_query=False)

                    if embedding_vector:
                        yield {
                            "_index": CHUNKED_INDEX_NAME,
                            "_id": f"{case_no}_{i}",
                            "_source": {
                                "id": case_no,
                                "caseNm": data.get("caseNm"),
                                "title": data.get("caseTitle"),
                                "category": data.get("Class_info", {}).get("class_name"),
                                "subcategory": data.get("Class_info", {}).get("instance_name"),
                                "court": data.get("courtNm"),
                                "date": data.get("judmnAdjuDe"),
                                "preview": data.get("jdgmn"),
                                "chunk_content": chunk,
                                "content_embedding": embedding_vector
                            }
                        }
                except Exception as api_err:
                    logging.error(f"API 에러 ({case_no}): {api_err}")
                    continue

        except Exception as e:
            logging.error(f"파일 {file_path.name} 처리 중 에러: {e}")


def index_documents():
    logging.info("Bulk 인덱싱 시작 (768차원 적용)")
    success, errors = helpers.bulk(
        opensearch_client,
        get_indexing_actions(),
        chunk_size=30,
        request_timeout=300,
        raise_on_error=False,
        raise_on_exception=False
    )
    logging.info(f"성공: {success}건, 실패: {len(errors) if isinstance(errors, list) else errors}건")


if __name__ == "__main__":
    # 1. 인덱스 초기화 (768차원)
    create_indices()
    # 2. 인덱싱 실행
    index_documents()