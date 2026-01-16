import logging
import os
from pathlib import Path
from time import time, sleep

import psycopg2
from psycopg2 import OperationalError

# 환경 변수 파일 로드 (로컬 실행 시 필요)
env_path = Path(__file__).resolve().parent / "backend.env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(env_path)


def postgres_is_ready():
    check_timeout = 300  # RDS 연결을 위해 타임아웃 증가 (5분)
    check_interval = 5
    start_time = time()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())

    # 환경 변수에서 DB 설정 가져오기
    db_host = os.getenv("DB_HOST", "postgres")
    db_user = os.getenv("DB_USER", "sa")
    db_password = os.getenv("DB_PASSWORD", "1234")
    db_name = os.getenv("DB_NAME", "mydatabase")
    db_port = int(os.getenv("DB_PORT", "5432"))

    logger.info(f"Attempting to connect to PostgreSQL at {db_host}:{db_port}")
    logger.info(f"Database: {db_name}, User: {db_user}")

    while time() - start_time < check_timeout:
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                dbname=db_name,
                connect_timeout=30,  # RDS 연결을 위해 타임아웃 증가
            )
            conn.close()
            logger.info("PostgreSQL Connected Successfully.")
            return True
        except OperationalError as e:
            elapsed = int(time() - start_time)
            error_msg = str(e)
            logger.info(f"[{elapsed}s] Waiting for PostgreSQL... ({error_msg})")
            
            # 타임아웃 관련 에러인 경우 추가 안내
            if "timeout" in error_msg.lower():
                logger.warning("  -> This might indicate:")
                logger.warning("     1. RDS is not 'Publicly Accessible'")
                logger.warning("     2. Security group is blocking the connection")
                logger.warning("     3. RDS is in a Private Subnet")
            
            sleep(check_interval)
        except Exception as e:
            elapsed = int(time() - start_time)
            logger.error(f"[{elapsed}s] Unexpected error: {e}")
            sleep(check_interval)

    logger.error(
        f"Could not connect to {db_host}:{db_port} within {check_timeout} seconds."
    )
    logger.error("Please check:")
    logger.error("  1. RDS 'Publicly Accessible' setting (must be Yes)")
    logger.error("  2. Security group allows your IP address")
    logger.error("  3. RDS is in a Public Subnet")
    logger.error("  4. RDS instance is in 'Available' status")
    return False


if __name__ == "__main__":
    postgres_is_ready()
