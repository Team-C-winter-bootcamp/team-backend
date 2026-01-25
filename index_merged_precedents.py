import os
import json
import logging
import re
import sys
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
    """
    판시사항, 판결요지, 판례내용을 합쳐서 \n 또는 . 기준으로 분리합니다.
    """
    combined_text = "\n".join([t for t in text_list if t])
    # \n 또는 . 뒤에 공백이 오는 패턴으로 분리
    chunks = re.split(r'[\n.]', combined_text)
    # 공백 제거 및 빈 문장 제외
    return [c.strip() for c in chunks if len(c.strip()) > 10]  # 최소 10자 이상만 의미 있는 청크로 간주


def create_indices():
    """모든 정보를 담을 수 있도록 인덱스 매핑 생성"""
    # 'reindex' 인자가 있으면 기존 인덱스 삭제
    if 'reindex' in sys.argv:
        logging.info("Re-indexing requested. Deleting existing indices.")
        if opensearch_client.indices.exists(index=CHUNKED_INDEX_NAME):
            opensearch_client.indices.delete(index=CHUNKED_INDEX_NAME)
            logging.info(f"Deleted index: {CHUNKED_INDEX_NAME}")
        if opensearch_client.indices.exists(index=PRECEDENTS_INDEX_NAME):
            opensearch_client.indices.delete(index=PRECEDENTS_INDEX_NAME)
            logging.info(f"Deleted index: {PRECEDENTS_INDEX_NAME}")

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
                    "판례일련번호": {"type": "integer"},
                    "caseNo": {"type": "keyword"},
                    "caseTitle": {"type": "text"},
                    "instance_name": {"type": "keyword"},
                    "chunk_content": {"type": "text"},
                    "summ_contxt": {"type": "text"}
                }
            }
        }
        opensearch_client.indices.create(index=CHUNKED_INDEX_NAME, body=body)
        logging.info(f"Created index: {CHUNKED_INDEX_NAME}")

    # 2. 전체 데이터 저장 인덱스 (전문 + 모든 필드)
    if not opensearch_client.indices.exists(index=PRECEDENTS_INDEX_NAME):
        body = {
            "mappings": {
                "properties": {
                    "판례일련번호": {"type": "integer"},
                    "caseNo": {"type": "keyword"},
                    "Reference_info": {"type": "object"},
                    "Class_info": {"type": "object"},
                    "Summary": {"type": "nested"},
                    "keyword_tagg": {"type": "nested"}
                }
            }
        }
        opensearch_client.indices.create(index=PRECEDENTS_INDEX_NAME, body=body)
        logging.info(f"Created index: {PRECEDENTS_INDEX_NAME}")


def index_documents():
    json_files = list(MERGED_DATA_DIR.glob("*.json"))
    logging.info(f"총 {len(json_files)}개 파일 인덱싱 시작")

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 필드 매핑 준비 (사용자 요청 규격)
            class_info = data.get("Class_info") or data.get("class_info", {})

            # 청킹 대상 필드 결합
            target_texts = [data.get("판시사항", ""), data.get("판결요지", ""), data.get("판례내용", "")]
            chunks = smart_split(target_texts)

            for i, chunk in enumerate(chunks):
                # Gemini 임베딩 생성
                res = genai_client.models.embed_content(model=EMBEDDING_MODEL, contents=chunk)

                chunk_body = {
                    "id": data.get("caseNo"),  # 사건번호
                    "caseNm": data.get("caseNm"),  # 사건명
                    "title": data.get("caseTitle"),  # 판례제목
                    "subcategory": class_info.get("instance_name"),  # 배임, 사기 등
                    "category": class_info.get("class_name"),  # 민사, 형사 등
                    "court": data.get("courtNm"),  # 법원명
                    "date": data.get("judmnAdjuDe"),  # 선고일자
                    "preview": data.get("jdgmn"),  # 미리보기
                    "chunk_content": chunk,  # 실제 청크 내용 추가
                    "content_embedding": res.embeddings[0].values  # 어짜피 한개만 embeding함
                }

                # 인덱싱 (ID는 중복 방지를 위해 사건번호_순번 사용)
                opensearch_client.index(
                    index=CHUNKED_INDEX_NAME,
                    body=chunk_body,
                    id=f"{data.get('caseNo')}_{i}"
                )

            logging.info(f"완료: {data.get('caseNo')}")

        except Exception as e:
            logging.error(f"실패: {file_path.name} -> {e}")


if __name__ == "__main__":
    create_indices()
    index_documents()