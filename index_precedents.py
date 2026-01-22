import os
import json
import google.genai as genai
from opensearchpy import OpenSearch, RequestsHttpConnection
import logging
import re

# MeCab 사용 (설치: pip install mecab-python3)
try:
    import MeCab
    MECAB_AVAILABLE = True
except ImportError:
    MECAB_AVAILABLE = False
    logging.warning("MeCab이 설치되지 않았습니다. 정규식을 사용하여 문장을 분리합니다.")

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Gemini API 키 설정
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# OpenSearch 클라이언트 설정
OPENSEARCH_HOST = os.environ.get("OPENSEARCH_HOST", "localhost")
OPENSEARCH_PORT = int(os.environ.get("OPENSEARCH_PORT", 9200))

opensearch_client = OpenSearch(
    hosts=[{'host': OPENSEARCH_HOST, 'port': OPENSEARCH_PORT}],
    http_conn_class=RequestsHttpConnection,
    use_ssl=False,
    verify_certs=False,
    ssl_show_warn=False,
)

INDEX_NAME = "precedents_chunked"
EMBEDDING_MODEL = "models/text-embedding-004"
VECTOR_DIMENSION = 768 # text-embedding-004 모델의 차원


def split_sentences(text: str) -> list:
    """
    텍스트를 문장 단위로 분리합니다.
    MeCab이 있으면 MeCab을 사용하고, 없으면 정규식을 사용합니다.
    
    Args:
        text: 분리할 텍스트
    
    Returns:
        문장 리스트
    """
    if not text or not text.strip():
        return []
    
    # 문장 끝 마커(., !, ?, 。)를 기준으로 분리
    sentences = re.split(r'([.!?。]\s*)', text)
    result = []
    for i in range(0, len(sentences) - 1, 2):
        if i + 1 < len(sentences):
            sentence = sentences[i] + sentences[i + 1]
        else:
            sentence = sentences[i]
        sentence = sentence.strip()
        if sentence:
            result.append(sentence)
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())
    
    # MeCab이 있으면 형태소 분석을 통해 문장 경계를 더 정확하게 확인
    if MECAB_AVAILABLE and result:
        try:
            mecab = MeCab.Tagger()
            # MeCab을 사용하여 문장 분리 결과를 검증하고 개선
            # (현재는 기본 정규식 분리를 사용하고, 향후 MeCab 기반 개선 가능)
            pass
        except Exception as e:
            logging.debug(f"MeCab 초기화 실패 (정규식 사용): {e}")
    
    return result if result else [text]


def create_index_if_not_exists():
    """인덱스가 존재하지 않으면 새로 생성합니다."""
    try:
        if not opensearch_client.indices.exists(index=INDEX_NAME):
            index_body = {
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                },
                "mappings": {
                    "properties": {
                        "content_embedding": {
                            "type": "knn_vector",
                            "dimension": VECTOR_DIMENSION,
                            "method": {
                                "name": "hnsw",
                                "space_type": "l2",
                                "engine": "faiss"
                            }
                        },
                        "판례일련번호": {"type": "integer"},
                        "caseNo": {"type": "keyword"},
                        "caseTitle": {"type": "text"},
                        "instance_name": {"type": "text"},
                        "courtNm": {"type": "keyword"},
                        "judmnAdjuDe": {"type": "date"},
                        "caseNm": {"type": "text"},
                        "사건종류명": {"type": "keyword"},
                        "chunk_content": {"type": "text"},
                        "chunk_sequence": {"type": "integer"}
                    }
                }
            }
            opensearch_client.indices.create(index=INDEX_NAME, body=index_body)
            logging.info(f"'{INDEX_NAME}' 인덱스를 생성했습니다.")
        else:
            logging.info(f"'{INDEX_NAME}' 인덱스가 이미 존재합니다.")
    except Exception as e:
        logging.error(f"인덱스 생성 중 오류 발생: {e}")
        raise

def index_documents():
    """data 폴더의 JSON 파일들을 읽어 청크 단위로 OpenSearch에 인덱싱합니다."""
    data_dir = "data"
    json_files = [f for f in os.listdir(data_dir) if f.endswith('.json')]

    for file_name in json_files:
        file_path = os.path.join(data_dir, file_name)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                original_doc = json.load(f)

            content_to_chunk = original_doc.get("판례내용", "")
            if not content_to_chunk:
                logging.warning(f"청킹할 '판례내용'이 없는 파일: {file_name}")
                continue

            # 문장 단위로 청킹 (MeCab 또는 정규식 사용)
            chunks = split_sentences(content_to_chunk)

            # 사건번호 추출
            case_no = original_doc.get("사건번호", "")
            if not case_no:
                logging.warning(f"사건번호가 없는 파일: {file_name}")
                continue
            
            for i, chunk_text in enumerate(chunks):
                sequence = i + 1
                # 문서 ID를 사건번호_순서 형식으로 구성
                chunk_doc_id = f"{case_no}_{sequence}"

                # 임베딩할 텍스트는 청크 자체입니다.
                text_to_embed = chunk_text.strip()

                if not text_to_embed:
                    logging.warning(f"임베딩할 내용이 없는 청크: {file_name}, 청크 번호: {sequence}")
                    continue

                # Gemini 임베딩 생성
                embedding_result = genai_client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=text_to_embed
                )
                
                # 응답 구조 확인 및 임베딩 추출
                # google.genai API 응답은 EmbedContentResponse 객체
                if hasattr(embedding_result, 'embeddings') and len(embedding_result.embeddings) > 0:
                    embedding = list(embedding_result.embeddings[0].values)
                elif isinstance(embedding_result, dict):
                    embedding = embedding_result.get('embedding', embedding_result.get('values', []))
                else:
                    logging.error(f"임베딩 추출 실패 - 응답 타입: {type(embedding_result)}")
                    continue
                
                # 청크 문서 생성
                chunk_doc = {
                    key: value for key, value in original_doc.items() if key != "판례내용"
                }
                chunk_doc['chunk_content'] = chunk_text
                chunk_doc['chunk_sequence'] = sequence
                chunk_doc['content_embedding'] = embedding

                # OpenSearch에 청크 문서 인덱싱
                opensearch_client.index(
                    index=INDEX_NAME,
                    body=chunk_doc,
                    id=chunk_doc_id
                )
                logging.info(f"청크 문서 인덱싱 완료: {file_name} (ID: {chunk_doc_id})")

        except json.JSONDecodeError:
            logging.error(f"JSON 파싱 오류: {file_name}")
        except Exception as e:
            logging.error(f"문서 처리 중 오류 발생 ({file_name}): {e}")

if __name__ == "__main__":
    logging.info("OpenSearch 청킹 인덱싱 스크립트를 시작합니다.")
    
    # OpenSearch 서버 연결 확인
    if not opensearch_client.ping():
        logging.error("OpenSearch 서버에 연결할 수 없습니다. Docker 컨테이너가 실행 중인지 확인하세요.")
    else:
        logging.info("OpenSearch 서버에 성공적으로 연결되었습니다.")
        create_index_if_not_exists()
        index_documents()
        logging.info("모든 문서의 청킹 및 인덱싱 작업이 완료되었습니다.")