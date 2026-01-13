# team-backend

## 로컬 Django 개발 환경
- 가상환경 생성 후 패키지 설치: `pip install -r requirements.txt`
- `.env` 파일을 프로젝트 루트에 생성하고 `env.example` 내용을 복사 후 값 채우기
- 서버 실행: `python manage.py runserver 0.0.0.0:8000`
- 브라우저 접속: `http://localhost:8000`

## Swagger / OpenAPI
- `drf-yasg` 추가로 `Swagger UI`, `Redoc`, JSON/YAML 스키마 제공
- 엔드포인트:
  - `http://localhost:8000/swagger/` (Swagger UI)
  - `http://localhost:8000/redoc/` (Redoc)
  - `http://localhost:8000/swagger.json` / `swagger.yaml`

## Docker 개발 환경
- `.env` 준비 후 빌드/실행:
  - `docker compose build`
  - `docker compose up`
- 내부에서 실행되는 명령:
  - `python manage.py migrate`
  - `python manage.py collectstatic --noinput`
  - `gunicorn config.wsgi:application --bind 0.0.0.0:8000`
- 접속: `http://localhost:8000`

## 환경 변수
- `env.example`를 참고하여 `.env` 생성
- 필수 키:
  - `DJANGO_SECRET_KEY`
  - `DEBUG` (예: True/False)
  - `ALLOWED_HOSTS` (쉼표로 구분)
