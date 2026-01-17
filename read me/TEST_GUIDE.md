# 테스트 가이드

## 1. 슈퍼유저 생성

Django Admin에 접근하기 위해 슈퍼유저를 생성해야 합니다.

### 방법 1: 스크립트 사용 (권장)
```bash
python create_superuser.py
```

### 방법 2: 수동 생성
```bash
python manage.py createsuperuser
```

입력 예시:
- Clerk id: `admin_user`
- Email: `admin@example.com`
- Password: (원하는 비밀번호 입력 - Clerk를 사용하므로 실제로는 사용되지 않음) -admin123-

**참고**: 로컬 개발 환경에서는 SQLite를 사용하도록 설정되어 있습니다. (`backend.env`의 `DB_HOST=sqlite`)

## 2. 서버 실행

```bash
python manage.py runserver
```

## 3. Django Admin 접근

브라우저에서 `http://localhost:8000/admin/` 접속 후 위에서 생성한 슈퍼유저로 로그인합니다.

## 4. 테스트 데이터 입력 순서

### 4.1 Precedents (판례) 앱 테스트

#### 1단계: 마스터 데이터 생성

**Category (대분류) 생성:**
- category_code: `1`
- category_name: `민사`

**SubCategory (소분류) 생성:**
- category: 위에서 생성한 Category 선택
- subcategory_name: `계약`

**Court (법원) 생성:**
- court_code: `1`
- court_type: `대법원`
- court_name: `대법원`

**Outcome (결과) 생성:**
- outcome_code: `1`
- outcome_type: `기각`

**Keyword (키워드) 생성:**
- name: `손해배상`

#### 2단계: Precedent (판례) 생성

- case_no: `2020가단12345`
- case_name: `○○ 대 ○○`
- case_title: `손해배상청구 사건`
- decision_type: `판결`
- judge_date: `2020-01-15`
- court: 위에서 생성한 Court 선택
- subcategory: 위에서 생성한 SubCategory 선택
- judgment_content: `【판결요지】 원고의 청구를 기각한다. 【이유】 원고는 피고를 상대로 손해배상을 청구하였으나, 피고에게 과실이 인정되지 않으므로 원고의 청구는 이유 없다.`

#### 3단계: 관계 데이터 연결

**RelationKeyword 생성:**
- precedent: 위에서 생성한 Precedent 선택
- keyword: 위에서 생성한 Keyword 선택

**RelationOutcome 생성:**
- precedent: 위에서 생성한 Precedent 선택
- outcome: 위에서 생성한 Outcome 선택
- outcome_value: `1` (선택사항)

### 4.2 Chats (채팅) 앱 테스트

#### 1단계: User 생성 (또는 기존 사용자 확인)

**User 생성:**
- clerk_id: `test_user_1`
- email: `test1@example.com`

#### 2단계: Session 생성

- user: 위에서 생성한 User 선택
- title: `법률 상담`
- bookmark: `False` (또는 `True`)

#### 3단계: Message 생성

**사용자 메시지:**
- session: 위에서 생성한 Session 선택
- role: `user`
- chat_order: `1`
- content: `안녕하세요, 계약 관련 상담을 받고 싶습니다.`

**AI 응답 메시지:**
- session: 같은 Session 선택
- role: `assistant`
- chat_order: `2`
- content: `안녕하세요! 계약 관련 상담을 도와드리겠습니다. 어떤 내용이 궁금하신가요?`

## 5. API 테스트 방법

### 5.1 Swagger UI 사용 (권장)

1. 브라우저에서 `http://localhost:8000/swagger/` 접속
2. 각 API 엔드포인트를 클릭하여 테스트
3. "Try it out" 버튼 클릭 후 요청 파라미터 입력
4. "Execute" 버튼으로 실행

### 5.2 Postman 사용

**인증 없이 테스트 (DEBUG 모드):**
- DEBUG 모드가 활성화되어 있으면 Authorization 헤더 없이 테스트 가능
- 또는 `X-Test-Mode: true` 헤더 추가

**테스트 예시:**

1. **세션 목록 조회**
   ```
   GET http://localhost:8000/api/sessions
   ```

2. **세션 생성**
   ```
   POST http://localhost:8000/api/sessions
   Content-Type: application/json
   
   {
     "message": "안녕하세요"
   }
   ```

3. **판례 목록 조회**
   ```
   GET http://localhost:8000/api/precedents/?q=손해배상
   ```

4. **판례 상세 조회**
   ```
   GET http://localhost:8000/api/precedents/1
   ```

## 6. 주의사항

1. **Foreign Key 관계**: Precedent을 생성하기 전에 Court, SubCategory가 먼저 생성되어 있어야 합니다.
2. **User와 Session**: Session을 생성하기 전에 User가 먼저 생성되어 있어야 합니다.
3. **Message와 Session**: Message를 생성하기 전에 Session이 먼저 생성되어 있어야 합니다.
4. **is_deleted 필드**: 논리 삭제를 사용하므로, 삭제된 데이터는 `is_deleted=True`로 표시됩니다.

## 7. 빠른 테스트를 위한 Fixture 사용 (선택사항)

대량의 테스트 데이터가 필요하다면 Django Fixture를 사용할 수 있습니다:

```bash
# 데이터 내보내기
python manage.py dumpdata precedents.Category precedents.SubCategory precedents.Court precedents.Outcome precedents.Keyword precedents.Precedent --indent 2 > fixtures/precedents_data.json

# 데이터 가져오기
python manage.py loaddata fixtures/precedents_data.json
```
