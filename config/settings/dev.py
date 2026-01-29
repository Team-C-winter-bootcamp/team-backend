from .base import *

env_path = os.path.join(BASE_DIR, "backend.env")
if os.path.exists(env_path):
    load_dotenv(env_path)

DEBUG = True
ALLOWED_HOSTS = ["*"]

DB_ENGINE = os.getenv("DB_ENGINE", "postgresql")
DB_HOST = os.getenv("DB_HOST", "postgres")

if DB_ENGINE == "postgresql" or DB_ENGINE == "django.db.backends.postgresql":
    # PostgreSQL 사용 (Docker 또는 RDS)
    DATABASES = {
        'default': {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "mydatabase"),
            "USER": os.getenv("DB_USER", "sa"),
            "PASSWORD": os.getenv("DB_PASSWORD", "1234"),
            "HOST": DB_HOST,
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {
                "connect_timeout": 30,  # RDS 연결을 위해 타임아웃 증가
            }
        }
    }

CORS_ORIGIN_ALLOW_ALL = True
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8000'
]
from opensearchpy import RequestsHttpConnection

import os

OPENSEARCH_CONFIG = {
    'hosts': [{
        'host': os.getenv('OPENSEARCH_HOST').replace('https://', '').replace('http://', ''), # 프로토콜 강제 제거
        'port': 443
    }],
    'http_auth': (os.getenv('OPENSEARCH_USERNAME'), os.getenv('OPENSEARCH_PASSWORD')),
    'use_ssl': True,              # 변수 대신 True 하드코딩으로 테스트
    'verify_certs': True,
    'connection_class': RequestsHttpConnection,
    'ssl_show_warn': False,
}

