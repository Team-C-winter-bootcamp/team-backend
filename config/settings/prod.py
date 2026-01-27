from .base import *
import os
from opensearchpy import RequestsHttpConnection

# 1. 보안 설정: 실서비스 환경이므로 False
DEBUG = False

# 2. 호스트 설정: EC2 IP와 DuckDNS 도메인 등록
ALLOWED_HOSTS = [
    os.getenv("EC2_PUBLIC_IP", "13.125.95.179"),
    "localhost",
    "127.0.0.1",
    "law-loading-api.duckdns.org",
]

# Swagger 설정: HTTPS 환경에서 리소스 차단을 방지하기 위한 핵심 설정
SWAGGER_SETTINGS = {
    'USE_SESSION_AUTH': False,
    'SECURITY_DEFINITIONS': None,
    'PROTOCOL_SET': ['https'],  # HTTP 대신 HTTPS를 쓰도록 강제
}

# 3. Traefik(HTTPS) 인식 설정: Mixed Content 에러 해결의 핵심
# 외부 프록시(Traefik)가 보낸 HTTPS 신호를 Django가 인식하게 함
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# 4. CORS 설정: Vercel 프론트엔드와 통신 허용
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://lawding.vercel.app",   
    "https://lawding.vercel.app/", 
    "https://law-loading-api.duckdns.org", # 본인 백엔드 주소
]

# 5. CSRF 설정: 보안 토큰 신뢰 도메인
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "https://lawding.vercel.app",
    "https://lawding.vercel.app/", 
    "https://law-loading-api.duckdns.org",
]

# 6. Database 설정 (PostgreSQL)
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

# 7. OpenSearch 설정
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

# 8. 정적 파일 설정
# collectstatic 실행 시 파일이 모이는 위치
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 9. HTTPS 보안 강화 설정
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
