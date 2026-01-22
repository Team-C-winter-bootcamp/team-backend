"""
병합된 판례 데이터를 OpenSearch에 인덱싱하는 스크립트
- precedents_chunked: 청킹된 문장들 + 임베딩
- precedents: 전체 판례 전문 (임베딩 없음)
"""
import os
import json
import google.genai as genai
from opensearchpy import OpenSearch, RequestsHttpConnection
import logging
import re
from pathlib import Path

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

CHUNKED_INDEX_NAME = "precedents_chunked"
PRECEDENTS_INDEX_NAME = "precedents"
EMBEDDING_MODEL = "models/text-embedding-004"
VECTOR_DIMENSION = 768  # text-embedding-004 모델의 차원

BASE_DIR = Path(__file__).parent
MERGED_DATA_DIR = BASE_DIR / "data" / "merged"


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
            pass
        except Exception as e:
            logging.debug(f"MeCab 초기화 실패 (정규식 사용): {e}")
    
    return result if result else [text]


def create_index_if_not_exists():
    """인덱스가 존재하지 않으면 새로 생성합니다."""
    # precedents_chunked 인덱스 생성 (청킹 + 임베딩용)
    try:
        if not opensearch_client.indices.exists(index=CHUNKED_INDEX_NAME):
            chunked_index_body = {
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
                        "caseNm": {"type": "text"},
                        "courtNm": {"type": "keyword"},
                        "judmnAdjuDe": {"type": "date"},
                        "판시사항": {"type": "text"},
                        "판결요지": {"type": "text"},
                        "jdgmn": {"type": "text"},
                        "사건종류명": {"type": "keyword"},
                        "instance_name": {"type": "text"},
                        "class_name": {"type": "keyword"},
                        "chunk_content": {"type": "text"},
                        "chunk_sequence": {"type": "integer"},
                        "summ_contxt": {"type": "text"},
                        "keyword_tagg": {"type": "nested"},
                        "Reference_info": {"type": "object"}
                    }
                }
            }
            opensearch_client.indices.create(index=CHUNKED_INDEX_NAME, body=chunked_index_body)
            logging.info(f"'{CHUNKED_INDEX_NAME}' 인덱스를 생성했습니다.")
        else:
            logging.info(f"'{CHUNKED_INDEX_NAME}' 인덱스가 이미 존재합니다.")
    except Exception as e:
        logging.error(f"인덱스 생성 중 오류 발생 ({CHUNKED_INDEX_NAME}): {e}")
        raise
    
    # precedents 인덱스 생성 (전문 저장용, 임베딩 없음)
    try:
        if not opensearch_client.indices.exists(index=PRECEDENTS_INDEX_NAME):
            precedents_index_body = {
                "mappings": {
                    "properties": {
                        "판례일련번호": {"type": "integer"},
                        "caseNo": {"type": "keyword"},
                        "caseTitle": {"type": "text"},
                        "caseNm": {"type": "text"},
                        "courtNm": {"type": "keyword"},
                        "judmnAdjuDe": {"type": "date"},
                        "판시사항": {"type": "text"},
                        "판결요지": {"type": "text"},
                        "판례내용": {"type": "text"},
                        "jdgmn": {"type": "text"},
                        "사건종류명": {"type": "keyword"},
                        "instance_name": {"type": "text"},
                        "class_name": {"type": "keyword"},
                        "summ_contxt": {"type": "text"},
                        "keyword_tagg": {"type": "nested"},
                        "Reference_info": {"type": "object"},
                        "Summary": {"type": "object"}
                    }
                }
            }
            opensearch_client.indices.create(index=PRECEDENTS_INDEX_NAME, body=precedents_index_body)
            logging.info(f"'{PRECEDENTS_INDEX_NAME}' 인덱스를 생성했습니다.")
        else:
            logging.info(f"'{PRECEDENTS_INDEX_NAME}' 인덱스가 이미 존재합니다.")
    except Exception as e:
        logging.error(f"인덱스 생성 중 오류 발생 ({PRECEDENTS_INDEX_NAME}): {e}")
        raise


def index_documents():
    """
    병합된 데이터 폴더의 JSON 파일들을 읽어 OpenSearch에 인덱싱합니다.
    - precedents_chunked: 청킹된 문장들 + 임베딩
    - precedents: 전체 판례 전문 (임베딩 없음)
    """
    if not MERGED_DATA_DIR.exists():
        logging.error(f"병합된 데이터 폴더가 없습니다: {MERGED_DATA_DIR}")
        return
    
    json_files = list(MERGED_DATA_DIR.glob("*.json"))
    
    if not json_files:
        logging.warning(f"병합된 데이터 폴더에 JSON 파일이 없습니다: {MERGED_DATA_DIR}")
        return
    
    logging.info(f"총 {len(json_files)}개의 병합된 JSON 파일을 찾았습니다.")
    
    indexed_count = 0
    chunk_count = 0
    error_count = 0
    
    for file_path in json_files:
        file_name = file_path.name
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                merged_doc = json.load(f)
            
            # 판례내용 추출
            content_to_chunk = merged_doc.get("판례내용", "")
            if not content_to_chunk:
                logging.warning(f"청킹할 '판례내용'이 없는 파일: {file_name}")
                continue
            
            # 문장 단위로 청킹 (MeCab 또는 정규식 사용)
            chunks = split_sentences(content_to_chunk)
            
            # Summary에서 summ_contxt 추출 (첫 번째 Summary 항목 사용)
            summ_contxt = ""
            if merged_doc.get("Summary") and len(merged_doc["Summary"]) > 0:
                summ_contxt = merged_doc["Summary"][0].get("summ_contxt", "")
            
            # Class_info에서 사건종류명 추출
            class_info = merged_doc.get("Class_info", {})
            사건종류명 = class_info.get("class_name", "")
            instance_name = class_info.get("instance_name", "")
            
            # 사건번호 추출
            case_no = merged_doc.get("caseNo", "")
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
                try:
                    embedding_result = genai_client.models.embed_content(
                        model=EMBEDDING_MODEL,
                        contents=text_to_embed
                    )
                    
                    # 응답 구조 확인 및 임베딩 추출
                    # google.genai API 응답은 EmbedContentResponse 객체
                    # 구조: embedding_result.embeddings[0].values
                    if hasattr(embedding_result, 'embeddings'):
                        # EmbedContentResponse 객체인 경우
                        if len(embedding_result.embeddings) > 0:
                            embedding = list(embedding_result.embeddings[0].values)
                        else:
                            logging.error(f"임베딩이 비어있습니다 ({file_name}, 청크 {sequence})")
                            continue
                    elif isinstance(embedding_result, dict):
                        # 딕셔너리 응답인 경우
                        if 'embedding' in embedding_result:
                            embedding = embedding_result['embedding']
                        elif 'embeddings' in embedding_result and len(embedding_result['embeddings']) > 0:
                            embedding = embedding_result['embeddings'][0].get('values', [])
                        elif 'values' in embedding_result:
                            embedding = embedding_result['values']
                        else:
                            logging.error(f"예상치 못한 응답 구조 ({file_name}, 청크 {sequence}): {embedding_result.keys()}")
                            continue
                    elif hasattr(embedding_result, 'embedding'):
                        embedding = embedding_result.embedding
                    elif hasattr(embedding_result, 'values'):
                        embedding = list(embedding_result.values) if not isinstance(embedding_result.values, list) else embedding_result.values
                    else:
                        logging.error(f"임베딩 추출 실패 - 응답 타입: {type(embedding_result)}, 내용: {embedding_result}")
                        continue
                    
                    # 임베딩이 리스트인지 확인
                    if not isinstance(embedding, list):
                        logging.error(f"임베딩이 리스트가 아닙니다 ({file_name}, 청크 {sequence}): {type(embedding)}")
                        continue
                    
                except Exception as e:
                    logging.error(f"임베딩 생성 실패 ({file_name}, 청크 {sequence}): {e}", exc_info=True)
                    continue
                
                # 청크 문서 생성
                chunk_doc = {
                    "판례일련번호": merged_doc.get("판례일련번호"),
                    "caseNo": merged_doc.get("caseNo", ""),
                    "caseTitle": merged_doc.get("caseTitle", ""),
                    "caseNm": merged_doc.get("caseNm", ""),
                    "courtNm": merged_doc.get("courtNm", ""),
                    "judmnAdjuDe": merged_doc.get("judmnAdjuDe", ""),
                    "판시사항": merged_doc.get("판시사항", ""),
                    "판결요지": merged_doc.get("판결요지", ""),
                    "jdgmn": merged_doc.get("jdgmn", ""),
                    "사건종류명": 사건종류명,
                    "instance_name": instance_name,
                    "class_name": 사건종류명,
                    "chunk_content": chunk_text,
                    "chunk_sequence": sequence,
                    "content_embedding": embedding,
                    "summ_contxt": summ_contxt,
                    "keyword_tagg": merged_doc.get("keyword_tagg", []),
                    "Reference_info": merged_doc.get("Reference_info", {})
                }
                
                # OpenSearch에 청크 문서 인덱싱 (precedents_chunked)
                opensearch_client.index(
                    index=CHUNKED_INDEX_NAME,
                    body=chunk_doc,
                    id=chunk_doc_id
                )
                chunk_count += 1
                
                if chunk_count % 10 == 0:
                    logging.info(f"진행 중... {chunk_count}개 청크 인덱싱 완료")
            
            # 전체 판례 문서를 precedents 인덱스에 저장 (임베딩 없음)
            # Summary에서 summ_contxt 추출 (첫 번째 Summary 항목 사용)
            summ_contxt = ""
            if merged_doc.get("Summary") and len(merged_doc["Summary"]) > 0:
                summ_contxt = merged_doc["Summary"][0].get("summ_contxt", "")
            
            # Class_info에서 사건종류명 추출
            class_info = merged_doc.get("Class_info", {})
            사건종류명 = class_info.get("class_name", "")
            instance_name = class_info.get("instance_name", "")
            
            # 전체 판례 문서 생성
            full_precedent_doc = {
                "판례일련번호": merged_doc.get("판례일련번호"),
                "caseNo": merged_doc.get("caseNo", ""),
                "caseTitle": merged_doc.get("caseTitle", ""),
                "caseNm": merged_doc.get("caseNm", ""),
                "courtNm": merged_doc.get("courtNm", ""),
                "judmnAdjuDe": merged_doc.get("judmnAdjuDe", ""),
                "판시사항": merged_doc.get("판시사항", ""),
                "판결요지": merged_doc.get("판결요지", ""),
                "판례내용": merged_doc.get("판례내용", ""),
                "jdgmn": merged_doc.get("jdgmn", ""),
                "사건종류명": 사건종류명,
                "instance_name": instance_name,
                "class_name": 사건종류명,
                "summ_contxt": summ_contxt,
                "keyword_tagg": merged_doc.get("keyword_tagg", []),
                "Reference_info": merged_doc.get("Reference_info", {}),
                "Summary": merged_doc.get("Summary", [])
            }
            
            # OpenSearch에 전체 판례 문서 인덱싱 (precedents)
            opensearch_client.index(
                index=PRECEDENTS_INDEX_NAME,
                body=full_precedent_doc,
                id=case_no
            )
            
            indexed_count += 1
            logging.info(f"문서 인덱싱 완료: {file_name} (청크 {len(chunks)}개, 전문 1개)")
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류 ({file_name}): {e}")
            error_count += 1
        except Exception as e:
            logging.error(f"문서 처리 중 오류 발생 ({file_name}): {e}")
            error_count += 1
    
    # 결과 요약
    logging.info("=" * 50)
    logging.info("인덱싱 작업 완료")
    logging.info(f"  - 처리된 문서: {indexed_count}개")
    logging.info(f"  - precedents_chunked: {chunk_count}개 청크")
    logging.info(f"  - precedents: {indexed_count}개 전문")
    logging.info(f"  - 오류: {error_count}개")


if __name__ == "__main__":
    try:
        logging.info("병합된 판례 데이터 OpenSearch 인덱싱 스크립트를 시작합니다.")
        
        # OpenSearch 서버 연결 확인
        try:
            if not opensearch_client.ping():
                logging.error("OpenSearch 서버에 연결할 수 없습니다. Docker 컨테이너가 실행 중인지 확인하세요.")
                logging.error(f"연결 시도 주소: {OPENSEARCH_HOST}:{OPENSEARCH_PORT}")
                exit(1)
        except Exception as e:
            logging.error(f"OpenSearch 서버 연결 확인 중 오류 발생: {e}")
            logging.error(f"연결 시도 주소: {OPENSEARCH_HOST}:{OPENSEARCH_PORT}")
            exit(1)
        
        logging.info("OpenSearch 서버에 성공적으로 연결되었습니다.")
        create_index_if_not_exists()
        index_documents()
        logging.info("모든 문서의 청킹 및 인덱싱 작업이 완료되었습니다.")
    except KeyboardInterrupt:
        logging.info("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        logging.error(f"예기치 않은 오류 발생: {e}", exc_info=True)
        exit(1)