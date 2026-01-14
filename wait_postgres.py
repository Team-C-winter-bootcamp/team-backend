import logging
import os
from time import time, sleep

import psycopg2
from psycopg2 import OperationalError


def postgres_is_ready():
    check_timeout = 120
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

    while time() - start_time < check_timeout:
        try:
            conn = psycopg2.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                dbname=db_name,
            )
            conn.close()
            logger.info("PostgreSQL Connected Successfully.")
            return True
        except OperationalError as e:
            logger.info(f"Waiting for PostgreSQL... ({e})")
            sleep(check_interval)

    logger.error(
        f"Could not connect to {db_host}:{db_port} within {check_timeout} seconds."
    )
    return False


if __name__ == "__main__":
    postgres_is_ready()
