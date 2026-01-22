"""
OpenSearch에 저장된 데이터를 확인하는 스크립트
"""
import os
from opensearchpy import OpenSearch, RequestsHttpConnection
import json

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


def check_connection():
    """OpenSearch 연결 확인"""
    try:
        if opensearch_client.ping():
            print("✓ OpenSearch 서버에 연결되었습니다.")
            return True
        else:
            print("✗ OpenSearch 서버에 연결할 수 없습니다.")
            return False
    except Exception as e:
        print(f"✗ 연결 오류: {e}")
        return False


def check_index_exists():
    """인덱스 존재 여부 확인"""
    try:
        exists = opensearch_client.indices.exists(index=INDEX_NAME)
        if exists:
            print(f"✓ 인덱스 '{INDEX_NAME}'가 존재합니다.")
            return True
        else:
            print(f"✗ 인덱스 '{INDEX_NAME}'가 존재하지 않습니다.")
            return False
    except Exception as e:
        print(f"✗ 인덱스 확인 오류: {e}")
        return False


def get_index_stats():
    """인덱스 통계 정보 조회"""
    try:
        stats = opensearch_client.indices.stats(index=INDEX_NAME)
        doc_count = stats['indices'][INDEX_NAME]['total']['docs']['count']
        print(f"\n인덱스 통계:")
        print(f"  - 총 문서 수: {doc_count:,}개")
        return doc_count
    except Exception as e:
        print(f"✗ 통계 조회 오류: {e}")
        return 0


def search_sample_documents(limit=5):
    """샘플 문서 검색"""
    try:
        query = {
            "size": limit,
            "query": {
                "match_all": {}
            },
            "_source": [
                "판례일련번호",
                "caseNo",
                "caseTitle",
                "caseNm",
                "courtNm",
                "chunk_sequence",
                "chunk_content"
            ]
        }
        
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        hits = response['hits']['hits']
        
        print(f"\n샘플 문서 {len(hits)}개:")
        print("=" * 80)
        
        for i, hit in enumerate(hits, 1):
            source = hit['_source']
            print(f"\n[{i}] 문서 ID: {hit['_id']}")
            print(f"    판례일련번호: {source.get('판례일련번호', 'N/A')}")
            print(f"    사건번호: {source.get('caseNo', 'N/A')}")
            print(f"    사건명: {source.get('caseNm', 'N/A')}")
            print(f"    사건제목: {source.get('caseTitle', 'N/A')}")
            print(f"    법원: {source.get('courtNm', 'N/A')}")
            print(f"    청크 순서: {source.get('chunk_sequence', 'N/A')}")
            chunk_content = source.get('chunk_content', '')
            if chunk_content:
                preview = chunk_content[:100] + "..." if len(chunk_content) > 100 else chunk_content
                print(f"    청크 내용: {preview}")
        
        return hits
    except Exception as e:
        print(f"✗ 문서 검색 오류: {e}")
        return []


def test_vector_search():
    """벡터 검색 테스트 (임베딩이 제대로 저장되었는지 확인)"""
    try:
        # 먼저 하나의 문서를 가져와서 임베딩 확인
        query = {
            "size": 1,
            "query": {
                "match_all": {}
            },
            "_source": ["content_embedding", "chunk_content", "caseTitle"]
        }
        
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        if response['hits']['total']['value'] == 0:
            print("\n✗ 검색할 문서가 없습니다.")
            return
        
        hit = response['hits']['hits'][0]
        source = hit['_source']
        embedding = source.get('content_embedding')
        
        if embedding:
            print(f"\n✓ 임베딩 벡터 확인:")
            print(f"  - 벡터 차원: {len(embedding)}")
            print(f"  - 문서 ID: {hit['_id']}")
            print(f"  - 사건제목: {source.get('caseTitle', 'N/A')}")
            print(f"  - 청크 내용 미리보기: {source.get('chunk_content', '')[:50]}...")
        else:
            print("\n✗ 임베딩 벡터가 없습니다.")
    except Exception as e:
        print(f"✗ 벡터 검색 테스트 오류: {e}")


def search_by_case_number(case_no: str):
    """사건번호로 검색"""
    try:
        query = {
            "size": 10,
            "query": {
                "term": {
                    "caseNo": case_no
                }
            },
            "_source": [
                "판례일련번호",
                "caseNo",
                "caseTitle",
                "chunk_sequence",
                "chunk_content"
            ]
        }
        
        response = opensearch_client.search(index=INDEX_NAME, body=query)
        hits = response['hits']['hits']
        
        print(f"\n사건번호 '{case_no}' 검색 결과: {len(hits)}개 청크")
        print("=" * 80)
        
        for i, hit in enumerate(hits, 1):
            source = hit['_source']
            print(f"\n[{i}] 청크 {source.get('chunk_sequence', 'N/A')}")
            chunk_content = source.get('chunk_content', '')
            if chunk_content:
                preview = chunk_content[:150] + "..." if len(chunk_content) > 150 else chunk_content
                print(f"    {preview}")
        
        return hits
    except Exception as e:
        print(f"✗ 검색 오류: {e}")
        return []


if __name__ == "__main__":
    print("=" * 80)
    print("OpenSearch 데이터 확인 스크립트")
    print("=" * 80)
    
    # 1. 연결 확인
    if not check_connection():
        exit(1)
    
    # 2. 인덱스 존재 확인
    if not check_index_exists():
        print("\n인덱스가 없습니다. 먼저 index_merged_precedents.py를 실행하세요.")
        exit(1)
    
    # 3. 통계 정보
    doc_count = get_index_stats()
    
    if doc_count == 0:
        print("\n인덱스에 문서가 없습니다. 먼저 index_merged_precedents.py를 실행하세요.")
        exit(1)
    
    # 4. 샘플 문서 검색
    search_sample_documents(limit=3)
    
    # 5. 벡터 검색 테스트
    test_vector_search()
    
    # 6. 특정 사건번호로 검색 (예시)
    print("\n" + "=" * 80)
    print("특정 사건번호로 검색 테스트")
    print("=" * 80)
    search_by_case_number("99다38613")
    
    print("\n" + "=" * 80)
    print("확인 완료!")
    print("=" * 80)
