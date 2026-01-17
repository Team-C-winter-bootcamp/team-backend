# Docker 사용 가이드

## 1. 사전 준비

### 1.1 환경 변수 파일 설정

`backend.env` 파일이 올바르게 설정되어 있는지 확인하세요:

```env
# Django
DJANGO_SETTINGS_MODULE=config.settings
DJANGO_SECRET_KEY=dev-secret-key  # 프로덕션에서는 강력한 키 사용
DJANGO_DEBUG=True

# PostgreSQL (Docker 환경)
DB_HOST=postgres  # docker-compose.yml의 서비스 이름
DB_PORT=5432
DB_NAME=mydatabase
DB_USER=sa
DB_PASSWORD=1234

# Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

## 2. Docker 실행

### 2.1 Docker Compose로 실행 (권장)

```bash
# 빌드 및 실행
docker compose up --build

# 백그라운드 실행
docker compose up -d --build

# 로그 확인
docker compose logs -f backend

# 특정 서비스만 재시작
docker compose restart backend
```

### 2.2 개별 명령어

```bash
# PostgreSQL 컨테이너만 실행
docker compose up postgres -d

# Backend 컨테이너만 실행
docker compose up backend -d

# 모든 컨테이너 중지
docker compose down

# 볼륨까지 삭제 (데이터 초기화)
docker compose down -v
```

## 3. 슈퍼유저 생성

Docker 컨테이너 내에서 슈퍼유저를 생성합니다:

```bash
# 방법 1: Docker exec 사용
docker compose exec backend python create_superuser.py

# 방법 2: Django 명령어 직접 실행
docker compose exec backend python manage.py createsuperuser
```

입력 예시:
- Clerk id: `admin_user`
- Email: `admin@example.com`
- Password: (원하는 비밀번호)

## 4. 마이그레이션

마이그레이션은 `docker-compose.yml`의 command에서 자동으로 실행되지만, 수동으로 실행하려면:

```bash
# 마이그레이션 생성
docker compose exec backend python manage.py makemigrations

# 마이그레이션 적용
docker compose exec backend python manage.py migrate
```

## 5. 접속 정보

### 5.1 API 서버
- URL: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/swagger/`
- ReDoc: `http://localhost:8000/redoc/`
- Admin: `http://localhost:8000/admin/`

### 5.2 PostgreSQL 데이터베이스
- Host: `localhost` (호스트에서 접속 시)
- Port: `5432`
- Database: `mydatabase`
- User: `sa`
- Password: `1234`

### 5.3 컨테이너 내부에서 접속
- Host: `postgres` (서비스 이름)
- Port: `5432`
- Database: `mydatabase`
- User: `sa`
- Password: `1234`

## 6. 데이터베이스 관리

### 6.1 PostgreSQL CLI 접속

```bash
# Docker 컨테이너 내부에서 접속
docker compose exec postgres psql -U sa -d mydatabase

# 호스트에서 직접 접속 (psql이 설치되어 있는 경우)
psql -h localhost -p 5432 -U sa -d mydatabase
```

### 6.2 데이터베이스 백업

```bash
# 백업
docker compose exec postgres pg_dump -U sa mydatabase > backup.sql

# 복원
docker compose exec -T postgres psql -U sa mydatabase < backup.sql
```

## 7. 개발 팁

### 7.1 코드 변경 반영

`docker-compose.yml`에서 볼륨 마운트(`./:/app`)가 설정되어 있으므로, 코드 변경 시 컨테이너를 재시작할 필요가 없습니다. 하지만 다음 경우에는 재시작이 필요합니다:

- `requirements.txt` 변경
- 환경 변수 변경
- `docker-compose.yml` 설정 변경

```bash
docker compose restart backend
```

### 7.2 로그 확인

```bash
# 모든 서비스 로그
docker compose logs

# Backend 로그만
docker compose logs backend

# 실시간 로그 확인
docker compose logs -f backend

# 최근 100줄만
docker compose logs --tail=100 backend
```

### 7.3 컨테이너 내부 접속

```bash
# Backend 컨테이너 접속
docker compose exec backend bash

# PostgreSQL 컨테이너 접속
docker compose exec postgres bash
```

### 7.4 Django Shell 사용

```bash
docker compose exec backend python manage.py shell
```

## 8. 문제 해결

### 8.1 PostgreSQL 연결 오류

```bash
# PostgreSQL 컨테이너 상태 확인
docker compose ps postgres

# PostgreSQL 로그 확인
docker compose logs postgres

# 컨테이너 재시작
docker compose restart postgres
```

### 8.2 마이그레이션 오류

```bash
# 마이그레이션 상태 확인
docker compose exec backend python manage.py showmigrations

# 특정 앱의 마이그레이션 되돌리기
docker compose exec backend python manage.py migrate chats zero

# 모든 마이그레이션 재적용
docker compose exec backend python manage.py migrate --run-syncdb
```

### 8.3 포트 충돌

포트 8000이나 5432가 이미 사용 중인 경우:

```yaml
# docker-compose.yml에서 포트 변경
ports:
  - "8001:8000"  # 호스트:컨테이너
```

## 9. 프로덕션 배포

프로덕션 환경에서는 다음 사항을 변경하세요:

1. **환경 변수**
   - `DJANGO_DEBUG=False`
   - `DJANGO_SECRET_KEY`를 강력한 키로 변경
   - `DB_PASSWORD`를 강력한 비밀번호로 변경

2. **설정 파일**
   - `config/settings/prod.py` 사용
   - `DJANGO_SETTINGS_MODULE=config.settings.prod`

3. **보안**
   - `ALLOWED_HOSTS` 설정
   - HTTPS 사용
   - 데이터베이스 백업 정기 실행

## 10. Docker Compose 명령어 요약

```bash
# 빌드 및 실행
docker compose up --build

# 백그라운드 실행
docker compose up -d

# 중지
docker compose stop

# 중지 및 삭제
docker compose down

# 볼륨까지 삭제
docker compose down -v

# 로그 확인
docker compose logs -f

# 상태 확인
docker compose ps

# 재시작
docker compose restart

# 특정 서비스 재시작
docker compose restart backend
```
