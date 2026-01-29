#!/usr/bin/env python
"""
gemini-embedding-001으로 임베딩 생성 후 차원(dimension) 확인 스크립트.
실행 전 .env.prod 또는 GEMINI_API_KEY가 설정되어 있어야 합니다.
"""
import os
import sys
from pathlib import Path

# 프로젝트 루트를 path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent))

# .env.prod 로드 (있으면)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env.prod"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
except ImportError:
    pass

from cases.service import GeminiService, EMBEDDING_MODEL_NAME


def main():
    if not os.environ.get("GEMINI_API_KEY"):
        print("오류: GEMINI_API_KEY가 설정되지 않았습니다. .env.prod 또는 환경 변수를 확인하세요.")
        sys.exit(1)

    test_text = "임베딩 차원 확인용 테스트 문장입니다."
    print(f"모델: {EMBEDDING_MODEL_NAME}")
    print(f"입력: {test_text!r}")
    print("임베딩 생성 중...")

    try:
        vec = GeminiService.create_embedding(test_text, is_query=True)
        dim = len(vec)
        print(f"차원(dimension): {dim}")
        print(f"벡터 길이(len): {dim}")
        if dim == 768:
            print("→ OpenSearch precedents_chunked 인덱스(768차원)와 일치합니다.")
        else:
            print(f"→ 주의: 인덱스는 768차원입니다. 현재 {dim}차원이면 검색 시 dimension 오류가 날 수 있습니다.")
    except Exception as e:
        print(f"오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
