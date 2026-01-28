import os
import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Any
from cases.service import GeminiService
import google.genai as genai
from opensearchpy import OpenSearch, RequestsHttpConnection

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 환경변수 로드
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / "backend.env")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 443))
OPENSEARCH_USERNAME = os.environ.get("OPENSEARCH_USERNAME")
OPENSEARCH_PASSWORD = os.environ.get("OPENSEARCH_PASSWORD")

# 모델 설정을 환경변수에서 가져오고 정제 (models/ 제거)
raw_embedding_model = os.environ.get("EMBEDDING_MODEL", "gemini-embedding-001")
EMBEDDING_MODEL = raw_embedding_model.replace("models/", "") if raw_embedding_model.startswith("models/") else raw_embedding_model
VECTOR_DIMENSION = 3072

if not all([OPENSEARCH_HOST, OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD]):
    raise RuntimeError("OpenSearch 환경변수가 설정되지 않았습니다.")

CHUNKED_INDEX_NAME = "precedents_chunked"
PRECEDENTS_INDEX_NAME = "precedents"
MERGED_DATA_DIR = Path(__file__).parent / "data" / "merged"

opensearch_client = OpenSearch(
    hosts=[{"host": OPENSEARCH_HOST, "port": OPENSEARCH_PORT}],
    http_auth=(OPENSEARCH_USERNAME, OPENSEARCH_PASSWORD),
    use_ssl=True,
    verify_certs=True,
)

genai_client = genai.Client(api_key=GEMINI_API_KEY)

def smart_split(text_list: List[str]) -> List[str]:
    combined_text = "\n".join([t for t in text_list if t])
    chunks = re.split(r'[\n.]', combined_text)
    return [c.strip() for c in chunks if len(c.strip()) > 10]

def create_indices():
    # ... (인덱스 생성 로직은 기존과 동일하므로 유지) ...
    if not opensearch_client.indices.exists(index=CHUNKED_INDEX_NAME):
        body = {
            "settings": {"index": {"knn": True}},
            "mappings": {
                "properties": {
                    "content_embedding": {
                        "type": "knn_vector", "dimension": VECTOR_DIMENSION,
                        "method": {"name": "hnsw", "space_type": "l2", "engine": "faiss"}
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
        opensearch_client.indices.create(index=CHUNKED_INDEX_NAME, body=body)

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
    logging.info(f"총 {len(json_files)}개 파일 인덱싱 시작 (모델: {EMBEDDING_MODEL})")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            case_no = data.get("caseNo")
            if not case_no:
                continue

            summary_texts = [s.get("summ_contxt", "") for s in data.get("Summary", [])]
            target_texts = [
                data.get("판시사항", ""),
                data.get("판결요지", ""),
                data.get("jdgmn", "")
            ] + summary_texts
            chunks = smart_split(target_texts)

            for i, chunk in enumerate(chunks):
                # 환경변수에서 가져온 정제된 모델명 사용
                embedding_vector = GeminiService.create_embedding(chunk, is_query=False)

                chunk_body = {
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

                opensearch_client.index(
                    index=CHUNKED_INDEX_NAME,
                    body=chunk_body,
                    id=f"{case_no}_{i}"
                )

            full_doc_body = {
                "case_no": case_no,
                "case_title": data.get("caseTitle"),
                "case_name": data.get("caseNm"),
                "court": data.get("courtNm"),
                "judgment_date": data.get("judmnAdjuDe"),
                "precedent_id": data.get("판례일련번호"),
                "issue": data.get("판시사항", ""),
                "content": data.get("판례내용", "")
            }

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