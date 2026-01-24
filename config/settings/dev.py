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

CORS_ORIGIN_ALLOW_ALL = True
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:3000',
    # 만약 다른 배포 주소가 있다면 여기에 추가
]
