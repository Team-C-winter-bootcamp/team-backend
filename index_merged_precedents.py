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
                    "id": case_no,  # case_no 대신 id
                    "caseNm": data.get("caseNm"),  # case_name 대신 caseNm
                    "title": data.get("caseTitle"),  # title 추가
                    "category": data.get("Class_info", {}).get("class_name"),  # 형사A(생활형) 등
                    "subcategory": data.get("Class_info", {}).get("instance_name"),  # 배임 등
                    "court": data.get("courtNm"),  # 법원명
                    "date": data.get("judmnAdjuDe"),  # 선고일자
                    "preview": data.get("jdgmn"),  # 미리보기 텍스트
                    "chunk_content": chunk,  # 검색된 텍스트 조각
                    "content_embedding": res.embeddings[0].values
                }

                opensearch_client.index(
                    index=CHUNKED_INDEX_NAME,
                    body=chunk_body,
                    id=f"{case_no}_{i}"
                )


            full_doc_body = {
                "case_no": case_no,  # "2001노688"
                "case_title": data.get("caseTitle"),  # "광주고등법원 2002. 3. 21. 선고..."
                "case_name": data.get("caseNm"),  # "특정경제범죄가중처벌등에관한법률위반..."
                "court": data.get("courtNm"),  # "광주고등법원"
                "judgment_date": data.get("judmnAdjuDe"),  # "2002-03-21" (정제된 날짜)
                "precedent_id": data.get("판례일련번호"),  # 71594 (숫자형)
                "issue": data.get("판시사항", ""),  # 【판시사항】 전문
                "content": data.get("판례내용", "")  # 【피고인】 전문
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