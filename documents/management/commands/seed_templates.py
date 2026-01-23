from django.core.management.base import BaseCommand
from documents.models import Template


# 사기 고소장 템플릿 정의
FRAUD_COMPLAINT_TEMPLATE = {
    "doc_type": "criminal_complaint_fraud",
    "name": "사기 고소장 v1",
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
        "written_date"
    ],
    "content_md": """# 고소장(사기)

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
고소인: {{complainant_name}} (서명)"""
}


class Command(BaseCommand):
    help = '사기 고소장 템플릿을 DB에 시드합니다. (idempotent)'

    def handle(self, *args, **options):
        self.stdout.write("템플릿 시드 시작...")

        template_data = FRAUD_COMPLAINT_TEMPLATE

        # doc_type과 version으로 기존 템플릿 조회
        template, created = Template.objects.update_or_create(
            doc_type=template_data["doc_type"],
            version=template_data["version"],
            defaults={
                "name": template_data["name"],
                "content_md": template_data["content_md"],
                "variables": template_data["variables"],
                "is_active": True,
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ 템플릿 생성됨: {template.name} (doc_type={template.doc_type}, version={template.version})'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f'✓ 템플릿 업데이트됨: {template.name} (doc_type={template.doc_type}, version={template.version})'
                )
            )

        self.stdout.write(self.style.SUCCESS("템플릿 시드 완료!"))
