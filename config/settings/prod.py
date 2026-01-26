from .base import *
import os
from opensearchpy import RequestsHttpConnection

DEBUG = False

ALLOWED_HOSTS = [
    os.getenv("EC2_PUBLIC_IP", "13.125.95.179"),
    "localhost",
    "127.0.0.1",
    "law-loading-api.duckdns.org", # 본인의 DuckDNS 주소로 변경
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://lawding.vercel.app", # 확인해주신 프론트 주소 반영
    "https://law-loading-api.duckdns.org", # 본인의 DuckDNS 주소로 변경
]

CSRF_TRUSTED_ORIGINS = [
    "https://lawding.vercel.app",
    "https://law-loading-api.duckdns.org",
]

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

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
