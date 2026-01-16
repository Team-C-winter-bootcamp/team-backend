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

### 빠른 시작

1. **환경 변수 파일 확인**
   - `backend.env` 파일이 존재하는지 확인
   - `DB_HOST=postgres`로 설정되어 있는지 확인

2. **Docker 실행**
   ```bash
   docker compose up --build
   ```

3. **슈퍼유저 생성** (별도 터미널)
   ```bash
   docker compose exec backend python create_superuser.py
   ```

4. **접속**
   - API: `http://localhost:8000`
   - Swagger: `http://localhost:8000/swagger/`
   - Admin: `http://localhost:8000/admin/`

### 상세 가이드

자세한 Docker 사용 방법은 [DOCKER_GUIDE.md](DOCKER_GUIDE.md)를 참고하세요.

### 주요 명령어

```bash
# 빌드 및 실행
docker compose up --build

# 백그라운드 실행
docker compose up -d

# 중지
docker compose down

# 로그 확인
docker compose logs -f backend

# 마이그레이션
docker compose exec backend python manage.py migrate

# 슈퍼유저 생성
docker compose exec backend python create_superuser.py
```

## 환경 변수
- `env.example`를 참고하여 `.env` 생성
- 필수 키:
  - `DJANGO_SECRET_KEY`
  - `DEBUG` (예: True/False)
  - `ALLOWED_HOSTS` (쉼표로 구분)
