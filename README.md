# Team Backend

Django/DRF 기반의 법률 서비스 백엔드 API

## 기능

- 판례 유사도 검색 (OpenSearch + Gemini Embedding)
- **문서 자동생성 (사기 고소장 등)**

## 실행 환경

- Docker + Docker Compose
- PostgreSQL 16
- OpenSearch

## 환경 설정

1. `backend.env.example`을 복사하여 `backend.env` 생성:

```bash
cp backend.env.example backend.env
```

2. `backend.env`에 필요한 환경변수 설정:

```env
# Gemini API (문서 자동생성에 필요)
GEMINI_API_KEY=your-gemini-api-key
```

## 실행 방법

### 1. 컨테이너 실행

```bash
docker compose up -d --build
```

### 2. 마이그레이션 (자동 실행됨)

docker-compose.yml에서 자동으로 실행되지만, 수동 실행이 필요한 경우:

```bash
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py migrate
```

### 3. 문서 템플릿 시드 (사기 고소장)

```bash
docker compose exec backend python manage.py seed_templates
```

출력 예시:
```
템플릿 시드 시작...
✓ 템플릿 생성됨: 사기 고소장 v1 (doc_type=criminal_complaint_fraud, version=1)
템플릿 시드 완료!
```

## API 문서

- Swagger UI: http://localhost:8000/swagger/
- ReDoc: http://localhost:8000/redoc/

---

## 문서 자동생성 API (PoC)

### POST /api/documents/generate

Gemini API를 사용하여 템플릿 기반 문서를 자동 생성합니다.

#### 요청

```json
{
  "doc_type": "criminal_complaint_fraud",
  "values": {
    "complainant_name": "홍길동",
    "complainant_contact": "010-1234-5678",
    ...
  }
}
```

#### 응답

```json
{
  "pass": true,
  "content_md": "# 고소장(사기)\n\n## 1. 고소인 인적사항\n...",
  "errors": []
}
```

#### 검증 규칙

| 에러 코드 | 설명 |
|----------|------|
| `UNRESOLVED_PLACEHOLDER` | `{{...}}` 플레이스홀더가 남아있음 |
| `MISSING_SECTION` | 템플릿의 헤더가 결과에 누락됨 |
| `EXTRA_SECTION` | 템플릿에 없는 헤더가 추가됨 |
| `TEMPLATE_NOT_FOUND` | 해당 doc_type의 템플릿이 없음 |

---

## curl 예시

### PASS 케이스 (모든 값 정상 제공)

```bash
curl -X POST http://localhost:8000/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{
    "doc_type": "criminal_complaint_fraud",
    "values": {
      "complainant_name": "홍길동",
      "complainant_contact": "010-1234-5678",
      "suspect_name": "김철수",
      "suspect_contact": "알 수 없음",
      "incident_datetime": "2025-12-10 14:30",
      "incident_place": "중고거래 채팅 및 계좌이체",
      "crime_facts": "중고거래로 30만원을 송금했으나 물품 미발송 및 연락두절",
      "damage_amount": "300,000원",
      "complaint_reason": "계획적 기망에 의한 재산상 피해",
      "evidence_list": ["계좌이체 내역", "채팅 캡처", "판매글 캡처"],
      "attachments": ["신분증 사본"],
      "request_purpose": "피고소인 처벌 및 피해금 환급",
      "written_date": "2026-01-22"
    }
  }'
```

예상 응답:
```json
{
  "pass": true,
  "content_md": "# 고소장(사기)\n\n## 1. 고소인 인적사항\n- 성명: 홍길동\n- 연락처: 010-1234-5678\n\n## 2. 피고소인 인적사항\n...",
  "errors": []
}
```

### FAIL 케이스 (템플릿 없음)

```bash
curl -X POST http://localhost:8000/api/documents/generate \
  -H "Content-Type: application/json" \
  -d '{
    "doc_type": "nonexistent_template",
    "values": {}
  }'
```

예상 응답:
```json
{
  "pass": false,
  "content_md": "",
  "errors": ["TEMPLATE_NOT_FOUND"]
}
```

### 참고: FAIL 케이스 (Gemini가 잘못 생성한 경우)

Gemini가 플레이스홀더를 치환하지 않거나 섹션을 추가한 경우 다음과 같은 응답이 반환됩니다:

```json
{
  "pass": false,
  "content_md": "# 고소장(사기)\n\n## 1. 고소인 인적사항\n- 성명: {{complainant_name}}\n...",
  "errors": ["UNRESOLVED_PLACEHOLDER"]
}
```

또는

```json
{
  "pass": false,
  "content_md": "# 고소장(사기)\n\n## 0. 개요\n...\n## 1. 고소인 인적사항\n...",
  "errors": ["EXTRA_SECTION"]
}
```

---

## 프로젝트 구조

```
team-backend/
├── config/                 # Django 설정
│   ├── settings/
│   │   ├── base.py
│   │   ├── dev.py
│   │   └── prod.py
│   └── urls.py
├── cases/                  # 판례 검색 앱
├── documents/              # 문서 자동생성 앱 (신규)
│   ├── models.py           # Template, Document 모델
│   ├── views.py            # DocumentGenerateView
│   ├── services.py         # Gemini 호출 서비스
│   ├── validators.py       # 문서 검증 로직
│   ├── serializers.py      # 요청/응답 시리얼라이저
│   ├── admin.py            # 관리자 페이지
│   └── management/
│       └── commands/
│           └── seed_templates.py  # 템플릿 시드 커맨드
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
