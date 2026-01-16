from .base import *

env_path = os.path.join(BASE_DIR, "backend.env")
if os.path.exists(env_path):
    load_dotenv(env_path)

DEBUG = True
ALLOWED_HOSTS = ["*"]

# 데이터베이스 설정
# DB_ENGINE 환경 변수로 데이터베이스 타입 결정
# "postgresql" 또는 "sqlite3" 중 선택 가능
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
else:
    # 로컬 환경: SQLite 사용 (PostgreSQL이 설치되어 있지 않은 경우)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

CORS_ORIGIN_ALLOW_ALL = True

# ========== S3 설정 (긴 텍스트 저장용) ==========
USE_S3 = os.getenv("USE_S3", "False").lower() == "true"

if USE_S3:
    # AWS S3 설정
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME", "ap-northeast-2")
    AWS_S3_CUSTOM_DOMAIN = os.getenv(
        "AWS_S3_CUSTOM_DOMAIN",
        f"{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com"
    )
    
    # S3 설정
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    AWS_DEFAULT_ACL = 'private'
    AWS_S3_VERIFY = True
    
    # 긴 텍스트 저장용 스토리지 (판례내용 등)
    DEFAULT_FILE_STORAGE = 'config.storage.TextStorage'
else:
    # 로컬 파일 시스템 사용
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    MEDIA_URL = '/media/'
