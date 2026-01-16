# 로그 확인 가이드

## 1. 실시간 로그 보기 (콘솔)

### 로컬 개발 환경

서버를 실행하면 터미널/콘솔에 실시간으로 로그가 출력됩니다:

```bash
python manage.py runserver
```

**출력 예시:**
```
INFO 2024-01-16 10:30:45,123 users.views DEBUG 모드: True, 받은 토큰: 'test_token_debug', 토큰 길이: 17
INFO 2024-01-16 10:30:45,125 users.views DEBUG 모드에서 테스트 토큰 사용됨
```

### Docker 환경

```bash
# 실시간 로그 보기
docker compose logs -f backend

# 최근 100줄 로그 보기
docker compose logs --tail=100 backend

# 특정 시간 이후 로그 보기
docker compose logs --since 10m backend
```

## 2. 파일 로그 보기

### 로그 파일 위치

```
backend/logs/django.log
```

### 로그 파일 확인 방법

**Windows (PowerShell):**
```powershell
# 실시간 로그 보기
Get-Content logs\django.log -Wait -Tail 50

# 전체 로그 보기
Get-Content logs\django.log

# 마지막 50줄 보기
Get-Content logs\django.log -Tail 50
```

**Windows (CMD):**
```cmd
# 마지막 50줄 보기
powershell -Command "Get-Content logs\django.log -Tail 50"
```

**Linux/Mac:**
```bash
# 실시간 로그 보기
tail -f logs/django.log

# 마지막 50줄 보기
tail -n 50 logs/django.log

# 전체 로그 보기
cat logs/django.log
```

## 3. 로그 레벨

현재 설정된 로그 레벨:
- **DEBUG**: 상세한 디버깅 정보 (개발 환경)
- **INFO**: 일반 정보 메시지
- **WARNING**: 경고 메시지
- **ERROR**: 오류 메시지
- **CRITICAL**: 심각한 오류 메시지

## 4. 주요 로그 메시지

### 사용자 인증 관련

```
DEBUG 모드: True, 받은 토큰: 'test_token_debug', 토큰 길이: 17
INFO DEBUG 모드에서 테스트 토큰 사용됨
WARNING DEBUG 모드가 비활성화되어 있습니다. 실제 Clerk 토큰이 필요합니다.
```

### API 요청 관련

```
INFO 2024-01-16 10:30:45,123 django.server "POST /api/users/token/verify/ HTTP/1.1" 200 123
```

## 5. 로그 필터링

### 특정 키워드 검색

**Windows (PowerShell):**
```powershell
# "DEBUG" 키워드가 포함된 로그만 보기
Get-Content logs\django.log | Select-String "DEBUG"

# "ERROR" 키워드가 포함된 로그만 보기
Get-Content logs\django.log | Select-String "ERROR"
```

**Linux/Mac:**
```bash
# "DEBUG" 키워드가 포함된 로그만 보기
grep "DEBUG" logs/django.log

# "ERROR" 키워드가 포함된 로그만 보기
grep "ERROR" logs/django.log
```

## 6. 로그 파일 관리

### 로그 파일 크기 제한

로그 파일이 너무 커지면 자동으로 로테이션되도록 설정할 수 있습니다. (현재는 수동 관리)

### 로그 파일 삭제

```bash
# Windows
del logs\django.log

# Linux/Mac
rm logs/django.log
```

## 7. 문제 해결

### 로그가 보이지 않는 경우

1. **로그 디렉토리 확인**
   ```bash
   # Windows
   dir logs
   
   # Linux/Mac
   ls -la logs/
   ```

2. **로그 설정 확인**
   - `config/settings/dev.py`에서 `LOGGING` 설정 확인
   - 서버 재시작

3. **권한 확인**
   - 로그 파일 쓰기 권한 확인

### 로그 레벨 변경

`config/settings/dev.py`에서 로그 레벨을 변경할 수 있습니다:

```python
'users': {
    'handlers': ['console', 'file'],
    'level': 'DEBUG',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'propagate': False,
},
```

## 8. 실전 예시

### DEBUG 모드와 토큰 확인

1. Swagger에서 `test_token_debug`로 API 호출
2. 터미널에서 다음 로그 확인:
   ```
   DEBUG users.views DEBUG 모드: True, 받은 토큰: 'test_token_debug', 토큰 길이: 17
   INFO users.views DEBUG 모드에서 테스트 토큰 사용됨
   ```

### 에러 발생 시

1. 에러 메시지 확인
2. 로그 파일에서 관련 로그 검색:
   ```powershell
   Get-Content logs\django.log | Select-String "ERROR" -Context 5
   ```
