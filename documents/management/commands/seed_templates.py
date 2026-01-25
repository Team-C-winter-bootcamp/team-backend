# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
from documents.models import Template


# =============================================================================
# 템플릿 정의
# =============================================================================

TEMPLATES = [
    # -------------------------------------------------------------------------
    # 1. 내용증명서 (proof_of_contents)
    # -------------------------------------------------------------------------
    {
        "doc_type": "내용증명서",
        "name": "내용증명서 v1",
        "version": 1,
        "variables": [
            "sender_name",
            "sender_address",
            "sender_contact",
            "receiver_name",
            "receiver_address",
            "transaction_date",
            "transaction_details",
            "claim_amount",
            "payment_deadline",
            "bank_account",
            "written_date",
        ],
        "content_md": """# 내용증명서

## 1. 발신인 정보
- 성명: {{sender_name}}
- 주소: {{sender_address}}
- 연락처: {{sender_contact}}

## 2. 수신인 정보
- 성명: {{receiver_name}}
- 주소: {{receiver_address}}

## 3. 거래 내역
- 거래일자: {{transaction_date}}
- 거래내용: {{transaction_details}}
- 청구금액: {{claim_amount}}

## 4. 요청 사항
위 거래와 관련하여 청구금액 {{claim_amount}}을 아래 계좌로 {{payment_deadline}}까지 지급하여 주시기 바랍니다.

만약 위 기한까지 이행하지 않을 경우, 민사상 법적 조치를 취할 것임을 알려드립니다.

## 5. 입금 계좌
{{bank_account}}

작성일: {{written_date}}
발신인: {{sender_name}} (인)""",
    },

    # -------------------------------------------------------------------------
    # 2. 고소장 (criminal_complaint_fraud)
    # -------------------------------------------------------------------------
    {
        "doc_type": "고소장",
        "name": "고소장 v1",
        "version": 1,
        "variables": [
            "complainant_name",
            "complainant_contact",
            "suspect_name",
            "suspect_contact",
            "request_purpose",
            "incident_datetime",
            "incident_place",
            "crime_facts",
            "damage_amount",
            "complaint_reason",
            "evidence_list",
            "attachments",
            "written_date",
        ],
        "content_md": """# 고소장

## 1. 고소인 인적사항
- 성명: {{complainant_name}}
- 연락처: {{complainant_contact}}

## 2. 피고소인 인적사항
- 성명: {{suspect_name}}
- 연락처: {{suspect_contact}}

## 3. 고소취지
{{request_purpose}}

## 4. 범죄사실
- 사건일시: {{incident_datetime}}
- 사건장소: {{incident_place}}
- 내용: {{crime_facts}}
- 피해금액: {{damage_amount}}

## 5. 고소이유
{{complaint_reason}}

## 6. 증거자료
{{evidence_list}}

## 7. 첨부자료
{{attachments}}

작성일: {{written_date}}
고소인: {{complainant_name}} (서명)""",
    },

    # -------------------------------------------------------------------------
    # 3. 합의서 (settlement_agreement)
    # -------------------------------------------------------------------------
    {
        "doc_type": "합의서",
        "name": "합의서 v1",
        "version": 1,
        "variables": [
            "party_a_name",
            "party_a_contact",
            "party_a_address",
            "party_b_name",
            "party_b_contact",
            "party_b_address",
            "incident_summary",
            "settlement_amount",
            "payment_method",
            "payment_deadline",
            "additional_terms",
            "written_date",
        ],
        "content_md": """# 합의서

## 1. 당사자

### 갑 (피해자)
- 성명: {{party_a_name}}
- 연락처: {{party_a_contact}}
- 주소: {{party_a_address}}

### 을 (가해자)
- 성명: {{party_b_name}}
- 연락처: {{party_b_contact}}
- 주소: {{party_b_address}}

## 2. 사건 개요
{{incident_summary}}

## 3. 합의 내용
1. 을은 갑에게 합의금 {{settlement_amount}}을 지급한다.
2. 지급 방법: {{payment_method}}
3. 지급 기한: {{payment_deadline}}

## 4. 추가 합의 조건
{{additional_terms}}

## 5. 효력
본 합의서 작성 후 갑은 을에 대한 민형사상 일체의 이의를 제기하지 않으며,
본 합의서는 작성일로부터 법적 효력을 발생한다.

작성일: {{written_date}}

갑: {{party_a_name}} (인)
을: {{party_b_name}} (인)""",
    },
]


# documents/management/commands/seed_templates.py

class Command(BaseCommand):
    help = "문서 템플릿을 DB에 시드합니다."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("템플릿 시드 시작..."))

        for data in TEMPLATES:
            # 매핑: doc_type -> type / content_md -> content
            # 모델에 없는 name, variables, version 필드는 무시하거나 defaults에서 제외해야 합니다.
            template, created = Template.objects.update_or_create(
                type=data["doc_type"] if "doc_type" in data else data["type"],
                defaults={
                    "content": data["content_md"] if "content_md" in data else data["content"],
                    "is_deleted": False,
                },
            )

            status = "생성" if created else "업데이트"
            self.stdout.write(self.style.SUCCESS(f"  [{status}] {template.type}"))

        self.stdout.write(self.style.SUCCESS("템플릿 시드 완료!"))