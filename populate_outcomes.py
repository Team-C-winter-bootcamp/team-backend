import os
import django

# Django 환경 설정
# settings.dev를 사용하도록 설정합니다. 프로젝트 구조에 따라 config.settings.prod 등으로 변경될 수 있습니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from precedents.models import Outcome

# 채워 넣을 데이터 목록
outcomes_data = [
    (1, "사형"),
    (2, "무기징역"),
    (3, "징역"),
    (4, "벌금"),
    (5, "금고"),
    (6, "집행유예"),
    (7, "기각"),
    (8, "파기"),
    (9, "각하"),
    (10, "면소"),
    (11, "인용"),
    (12, "무죄"),
    (13, "기타"),
]

def populate_outcomes():
    print("Outcome 데이터 채우기 시작...")
    for code, type_name in outcomes_data:
        # outcome_code를 기준으로 데이터를 찾거나 생성합니다.
        # 이미 존재하는 경우 outcome_type을 업데이트하지 않고 건너뜁니다.
        # outcome_code는 고유하다고 가정합니다.
        outcome, created = Outcome.objects.get_or_create(
            outcome_code=code,
            defaults={'outcome_type': type_name} # 새로 생성될 경우 outcome_type 설정
        )
        if created:
            print(f"생성됨: Outcome(outcome_code={code}, outcome_type='{type_name}')")
        else:
            print(f"이미 존재함 (건너뜀): Outcome(outcome_code={code}, outcome_type='{type_name}')")

if __name__ == '__main__':
    populate_outcomes()
