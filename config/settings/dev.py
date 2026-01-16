from .base import *

env_path = os.path.join(BASE_DIR, "backend.env")
if os.path.exists(env_path):
    load_dotenv(env_path)

DEBUG = True
ALLOWED_HOSTS = ["*"]

# 데이터베이스 설정
# 로컬 개발 환경: DB_HOST가 "postgres" (Docker)가 아니면 SQLite 사용
DB_HOST = os.getenv("DB_HOST", "postgres")

if DB_HOST == "postgres":
    # Docker 환경: PostgreSQL 사용
    DATABASES = {
        'default': {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "mydatabase"),
            "USER": os.getenv("DB_USER", "sa"),
            "PASSWORD": os.getenv("DB_PASSWORD", "1234"),
            "HOST": DB_HOST,
            "PORT": os.getenv("DB_PORT", "5432"),
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
