"""
PostgreSQL/RDS 연결 대기 스크립트
Docker 컨테이너 시작 시 데이터베이스가 준비될 때까지 대기
"""
import os
import sys
import time
import psycopg2
from psycopg2 import OperationalError

# 환경변수에서 데이터베이스 설정 읽기
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "mydatabase")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1234")

# RDS를 사용하는 경우 DB_HOST가 RDS 엔드포인트일 수 있음
# DB_ENGINE이 sqlite3이면 스킵
DB_ENGINE = os.getenv("DB_ENGINE", "postgresql")

if DB_ENGINE == "sqlite3":
    print("[INFO] SQLite 사용 중이므로 PostgreSQL 연결 대기를 건너뜁니다.")
    sys.exit(0)

max_retries = 30
retry_delay = 2

print(f"[INFO] PostgreSQL 연결 대기 중...")
print(f"  Host: {DB_HOST}")
print(f"  Port: {DB_PORT}")
print(f"  Database: {DB_NAME}")
print(f"  User: {DB_USER}")

for i in range(max_retries):
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            connect_timeout=5
        )
        conn.close()
        print(f"[SUCCESS] PostgreSQL 연결 성공!")
        sys.exit(0)
    except OperationalError as e:
        if i < max_retries - 1:
            print(f"[RETRY {i+1}/{max_retries}] 연결 실패, {retry_delay}초 후 재시도... ({str(e)[:50]})")
            time.sleep(retry_delay)
        else:
            print(f"[ERROR] {max_retries}번 시도 후에도 연결 실패")
            print(f"  오류: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] 예상치 못한 오류: {e}")
        sys.exit(1)

print(f"[ERROR] 최대 재시도 횟수({max_retries}) 초과")
sys.exit(1)
