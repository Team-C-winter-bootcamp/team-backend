from .base import *
import os

# 1. 보안 설정: 운영 환경에서는 반드시 False
DEBUG = False

# 2. 호스트 설정: EC2 IP와 로컬 접속 허용
# 환경 변수에 EC2_PUBLIC_IP를 등록해두면 관리가 편합니다.
ALLOWED_HOSTS = [
    os.getenv("EC2_PUBLIC_IP", "13.125.95.179"), # 현재 EC2 IP
    "localhost",
    "127.0.0.1",
]

# 3. CORS 설정: 프론트 배포 전이므로 임시로 모두 허용
# 프론트 배포 후에는 반드시 특정 도메인만 허용하도록 수정해야 합니다.
CORS_ALLOW_ALL_ORIGINS = True

# 4. CSRF 설정: 프론트엔드(localhost:3000)에서 오는 요청을 신뢰하도록 설정
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    f"http://{os.getenv('EC2_PUBLIC_IP', '13.125.95.179')}",
]

# 5. Database 설정 (이미 작성하신 내용 반영)
DB_ENGINE = os.getenv("DB_ENGINE", "postgresql")
DB_HOST = os.getenv("DB_HOST", "postgres")

if DB_ENGINE in ["postgresql", "django.db.backends.postgresql"]:
    DATABASES = {
        'default': {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "mydatabase"),
            "USER": os.getenv("DB_USER", "sa"),
            "PASSWORD": os.getenv("DB_PASSWORD", "1234"),
            "HOST": DB_HOST,
            "PORT": os.getenv("DB_PORT", "5432"),
            "OPTIONS": {
                "connect_timeout": 30,
            }
        }
    }

# 6. OpenSearch 설정 (작성하신 내용 최적화)
from opensearchpy import RequestsHttpConnection

OPENSEARCH_CONFIG = {
    'hosts': [{
        'host': os.getenv('OPENSEARCH_HOST', '').replace('https://', '').replace('http://', ''),
        'port': 443
    }],
    'http_auth': (os.getenv('OPENSEARCH_USER'), os.getenv('OPENSEARCH_PASSWORD')),
    'use_ssl': True,
    'verify_certs': True,
    'connection_class': RequestsHttpConnection,
    'ssl_show_warn': False,
}

# 7. 정적 파일 및 미디어 파일 루트 설정
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')