# Swagger에서 Bearer 토큰 사용 가이드

## 1. 실제 Clerk 토큰 사용 (권장)

### Clerk에서 토큰 얻는 방법

1. **Clerk Dashboard 접속**
   - https://dashboard.clerk.com 접속
   - 로그인 후 프로젝트 선택

2. **토큰 얻는 방법**

   **방법 A: 프론트엔드에서 토큰 가져오기**
   ```javascript
   // Clerk를 사용하는 프론트엔드 코드
   const token = await window.Clerk.session.getToken();
   console.log(token); // 이 토큰을 Swagger에 복사
   ```

   **방법 B: 브라우저 개발자 도구 사용**
   - 프론트엔드 애플리케이션에서 로그인
   - 개발자 도구 (F12) → Console 탭
   - `await window.Clerk.session.getToken()` 실행
   - 출력된 토큰 복사

3. **Swagger에서 사용**
   - Swagger UI 페이지에서 **"Authorize"** 버튼 클릭
   - Value 필드에 `Bearer [복사한_토큰]` 형식으로 입력
   - 또는 `[복사한_토큰]`만 입력 (Bearer는 자동으로 추가됨)
   - **Authorize** 클릭

## 2. DEBUG 모드에서 테스트 토큰 사용 (개발 환경 전용)

**개발 환경에서 실제 Clerk 토큰 없이 테스트할 수 있습니다!**

### 사용 방법

1. **서버가 DEBUG 모드로 실행 중인지 확인**
   - `config/settings/dev.py`에서 `DEBUG = True` 확인
   - 또는 `.env` 파일에서 `DEBUG=True` 확인

2. **Swagger에서 테스트 토큰 사용**
   - Swagger UI 페이지 (`http://localhost:8000/swagger/`) 접속
   - **"Authorize"** 버튼 클릭
   - Value 필드에 `test_token_debug` 입력
   - **Authorize** 클릭

3. **테스트**
   - 이제 모든 API가 `test_token_debug` 토큰으로 작동합니다
   - `/api/users/me/` API는 자동으로 테스트용 사용자를 생성/조회합니다

### 주의사항

- ⚠️ **DEBUG 모드에서만 작동**: 프로덕션 환경(`DEBUG=False`)에서는 실제 Clerk 토큰이 필요합니다
- ⚠️ **보안**: `test_token_debug`는 개발/테스트 용도로만 사용하세요
- ✅ **편의성**: 실제 Clerk 인증 설정 없이도 API를 테스트할 수 있습니다

## 3. Swagger UI에서 Bearer 토큰 입력 방법

1. Swagger UI 페이지 (`http://localhost:8000/swagger/`) 접속
2. 페이지 상단의 **"Authorize"** 버튼 클릭 (🔒 아이콘)
3. **Value** 필드에 다음 중 하나 입력:
   - `Bearer your_clerk_token_here` (권장)
   - `your_clerk_token_here` (Bearer 자동 추가)
4. **Authorize** 버튼 클릭
5. **Close** 클릭

이제 모든 API 요청에 자동으로 Bearer 토큰이 포함됩니다.

## 4. 예시

### 올바른 형식
```
Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMzQ1IiwiaXNzIjoiaHR0cHM6Ly9jbGVyay5hY2NvdW50cy5kZXYiLCJleHAiOjE3MDEyMzQ1Njd9...
```

또는

```
eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyXzEyMzQ1IiwiaXNzIjoiaHR0cHM6Ly9jbGVyay5hY2NvdW50cy5kZXYiLCJleHAiOjE3MDEyMzQ1Njd9...
```

## 5. 주의사항

- **프로덕션 환경**: 반드시 실제 Clerk에서 발급받은 유효한 토큰만 사용
- **토큰 만료**: Clerk 토큰은 만료 시간이 있으므로, 만료되면 새로 발급받아야 함
- **보안**: 토큰은 절대 공유하거나 Git에 커밋하지 마세요

## 6. 문제 해결

### "토큰이 만료되었습니다" 오류
- Clerk Dashboard에서 새 토큰 발급
- 프론트엔드에서 `session.getToken()` 다시 호출

### "토큰 검증에 실패했습니다" 오류
- 토큰이 올바른 형식인지 확인 (JWT 형식)
- `Bearer ` 접두사가 올바르게 포함되었는지 확인
- Clerk 프로젝트 설정이 올바른지 확인
