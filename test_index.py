"""간단한 테스트 스크립트"""
import sys
import os

# 환경 변수 확인
print("환경 변수 확인:")
print(f"  GEMINI_API_KEY: {'설정됨' if os.environ.get('GEMINI_API_KEY') else '설정 안됨'}")
print(f"  OPENSEARCH_HOST: {os.environ.get('OPENSEARCH_HOST', 'localhost')}")
print(f"  OPENSEARCH_PORT: {os.environ.get('OPENSEARCH_PORT', '9200')}")

# OpenSearch 연결 테스트
try:
    from opensearchpy import OpenSearch
    client = OpenSearch(
        hosts=[{'host': os.environ.get('OPENSEARCH_HOST', 'localhost'), 'port': int(os.environ.get('OPENSEARCH_PORT', 9200))}],
        use_ssl=False,
        verify_certs=False
    )
    ping_result = client.ping()
    print(f"\nOpenSearch 연결: {'성공' if ping_result else '실패'}")
except Exception as e:
    print(f"\nOpenSearch 연결 오류: {e}")

# 데이터 폴더 확인
from pathlib import Path
merged_dir = Path("data/merged")
if merged_dir.exists():
    json_files = list(merged_dir.glob("*.json"))
    print(f"\n병합된 데이터 파일: {len(json_files)}개")
    if json_files:
        print(f"  예시: {json_files[0].name}")
else:
    print(f"\n병합된 데이터 폴더가 없습니다: {merged_dir}")

print("\n테스트 완료!")
