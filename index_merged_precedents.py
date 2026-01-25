import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any

import google.genai as genai
from opensearchpy import OpenSearch, RequestsHttpConnection

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 설정값
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 9200))

CHUNKED_INDEX_NAME = "precedents_chunked"
PRECEDENTS_INDEX_NAME = "precedents"
EMBEDDING_MODEL = "models/text-embedding-004"
VECTOR_DIMENSION = 768

MERGED_DATA_DIR = Path(__file__).parent / "data" / "merged"

# 클라이언트 초기화
genai_client = genai.Client(api_key=GEMINI_API_KEY)
opensearch_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_conn_class=RequestsHttpConnection,
    use_ssl=False, verify_certs=False,
)

def smart_split(text_list: List[str]) -> List[str]:
    combined_text = "\n".join([t for t in text_list if t])
    chunks = re.split(r'[\n.]', combined_text)
    return [c.strip() for c in chunks if len(c.strip()) > 10]

def create_indices():
    """OpenSearch 인덱스 매핑 생성"""
    # 1. 벡터 검색 인덱스 (청크 단위)
    if not opensearch_client.indices.exists(index=CHUNKED_INDEX_NAME):
        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "content_embedding": {
                        "type": "knn_vector", "dimension": VECTOR_DIMENSION,
                        "method": {"name": "hnsw", "space_type": "l2", "engine": "faiss"}
                    },
                    "caseNo": {"type": "keyword"},
                    "caseNm": {"type": "text"},
                    "chunk_content": {"type": "text"}
                }
            }
        }
        opensearch_client.indices.create(index=CHUNKED_INDEX_NAME, body=body)

    # 2. 전체 데이터 저장 인덱스 (TypeScript PrecedentDetailData 규격 반영)
    if not opensearch_client.indices.exists(index=PRECEDENTS_INDEX_NAME):
        body = {
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
        opensearch_client.indices.create(index=PRECEDENTS_INDEX_NAME, body=body)

def index_documents():
    json_files = list(MERGED_DATA_DIR.glob("*.json"))
    logging.info(f"총 {len(json_files)}개 파일 인덱싱 시작")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # JSON 데이터 추출
            case_no = data.get("caseNo")
            if not case_no:
                logging.warning(f"사건번호 누락: {file_path.name}")
                continue

            # --- 1. precedents_chunked 인덱싱 (벡터 검색용) ---
            summary_texts = [s.get("summ_contxt", "") for s in data.get("Summary", [])]
            target_texts = [
                data.get("판시사항", ""),
                data.get("판결요지", ""),
                data.get("jdgmn", "")
            ] + summary_texts
            chunks = smart_split(target_texts)

            for i, chunk in enumerate(chunks):
                res = genai_client.models.embed_content(model=EMBEDDING_MODEL, contents=chunk)
                chunk_body = {
                    "caseNo": case_no,
                    "caseNm": data.get("caseNm"),
                    "chunk_content": chunk,
                    "content_embedding": res.embeddings[0].values
                }
                opensearch_client.index(
                    index=CHUNKED_INDEX_NAME,
                    body=chunk_body,
                    id=f"{case_no}_{i}"
                )

            # --- 2. precedents 인덱싱 (TypeScript 타입 규격 매핑) ---
            full_doc_body = {
                "case_no": case_no,                               # 2001노688
                "case_title": data.get("caseTitle"),              # 광주고등법원...
                "case_name": data.get("caseNm"),                 # 특정경제범죄...
                "court": data.get("courtNm"),                    # 광주고등법원
                "judgment_date": data.get("judmnAdjuDe"),        # 2002-03-21
                "precedent_id": data.get("판례일련번호"),           # 71594
                "issue": data.get("판시사항", ""),                # 【판시사항】...
                "content": data.get("판례내용", "")               # 【피고인】... 전문
            }

            # id=case_no를 명시하여 무작위 ID 생성을 방지하고 사건번호로 직접 GET 가능하게 함
            opensearch_client.index(
                index=PRECEDENTS_INDEX_NAME,
                body=full_doc_body,
                id=case_no
            )

            logging.info(f"인덱싱 성공: {case_no}")

        except Exception as e:
            logging.error(f"실패: {file_path.name} -> {e}")

if __name__ == "__main__":
    create_indices()
    index_documents()