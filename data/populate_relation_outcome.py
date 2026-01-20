import os
import django
import json
import glob
import re

# Django 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from precedents.models import Precedent, Outcome, RelationOutcome
from django.db import transaction

def extract_order_text(content):
    """'주문'과 '이유' 사이의 텍스트를 추출하는 함수"""
    # 다양한 패턴을 처리하기 위한 정규표현식
    # DOTALL 플래그는 '.'이 줄바꿈 문자도 포함하도록 함
    pattern = re.compile(r'【?\s*주\s*문\s*】?(.*?)【?\s*이\s*유\s*】?', re.DOTALL)
    match = pattern.search(content)
    if match:
        return match.group(1).strip()
    return ""

def find_outcome(order_text, outcomes):
    """주문 텍스트에서 outcome을 찾아 반환하는 함수. PK ID가 가장 낮은 것을 우선적으로 선택한다."""
    best_match_id = 13  # 기본값 '기타'
    min_found_id = float('inf')  # 찾은 가장 작은 ID를 저장

    # PK 1-12에 해당하는 outcome_type을 검색
    for outcome_id, outcome_type in outcomes.items():
        if outcome_id == 13:
            continue  # '기타'는 순회에서 제외

        if outcome_type in order_text:
            # 현재 찾은 ID가 이전에 찾은 ID보다 작으면 업데이트
            if outcome_id < min_found_id:
                min_found_id = outcome_id
                best_match_id = outcome_id
    
    return best_match_id

@transaction.atomic
def populate_relations():
    print("--- Starting RelationOutcome Population Script ---")

    # Outcome 데이터를 미리 메모리에 로드
    outcomes = {o.id: o.outcome_type for o in Outcome.objects.filter(id__in=range(1, 14))}
    if not outcomes:
        print("[Error] Outcome data not found in the database. Please run the script to populate outcomes first.")
        return

    print(f"Successfully loaded {len(outcomes)} outcome types from the database.")

    # 처리할 파일 경로 패턴
    path_patterns = [
        '1.데이터/Training/01.원천데이터/**/*.json',
        '1.데이터/Validation/01.원천데이터/**/*.json'
    ]

    # 모든 JSON 파일 목록을 가져옴
    file_paths = []
    for pattern in path_patterns:
        file_paths.extend(glob.glob(pattern, recursive=True))

    if not file_paths:
        print("[Error] No JSON files found. Please check the path patterns and directory structure.")
        print(f"Searched patterns: {path_patterns}")
        return

    print(f"Found {len(file_paths)} total JSON files to process.")

    # 카운터 초기화
    total_files = len(file_paths)
    processed_count = 0
    precedent_not_found_count = 0
    created_count = 0
    updated_count = 0

    # 각 파일을 순회하며 처리
    for i, file_path in enumerate(file_paths):
        print(f"--- Processing file {i+1}/{total_files}: {file_path} ---")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 1. 사건번호로 Precedent 찾기
            raw_case_no = data.get("사건번호", "")
            if not raw_case_no:
                print(f"[Warning] '사건번호' not found in file. Skipping.")
                continue
            
            case_no = raw_case_no.split(',')[0].strip()
            precedent = Precedent.objects.filter(case_no=case_no).first()

            if not precedent:
                print(f"[Warning] Precedent with case_no '{case_no}' not found in DB. Skipping.")
                precedent_not_found_count += 1
                continue

            # 2. '주문' 내용 추출 (새로운 규칙 적용)
            order_text = data.get("주문")  # "주문" 필드가 있는지 먼저 확인

            if not order_text:
                # "주문" 필드가 없으면 기존 방식으로 "판례내용"에서 추출
                content = data.get("판례내용", "")
                order_text = extract_order_text(content)
            
            if not order_text:
                print(f"[Info] '주문' text could not be found. Defaulting to '기타'.")
                outcome_id = 13 # 주문을 못찾으면 기타
            else:
                # 3. 주문 내용에서 Outcome 결정
                outcome_id = find_outcome(order_text, outcomes)
                print(f"[Info] Found order text. Matched outcome: ID {outcome_id}")

            # 4. Outcome 객체 가져오기
            target_outcome = Outcome.objects.get(id=outcome_id)

            # 5. RelationOutcome 생성 또는 업데이트
            relation, created = RelationOutcome.objects.update_or_create(
                precedent=precedent,
                defaults={'outcome': target_outcome}
            )

            if created:
                created_count += 1
                print(f"[Success] Created: Relation for Precedent '{precedent.case_no}' with Outcome '{target_outcome.outcome_type}'")
            else:
                updated_count += 1
                print(f"[Success] Updated: Relation for Precedent '{precedent.case_no}' with Outcome '{target_outcome.outcome_type}'")
            
            processed_count += 1

        except json.JSONDecodeError:
            print(f"[Error] Could not decode JSON from file. Skipping.")
        except Exception as e:
            print(f"[Critical Error] An unexpected error occurred: {e}")

    print("\n--- Finished Population Script ---")
    print("--- Summary ---")
    print(f"Total files found: {total_files}")
    print(f"Successfully processed files (relations created/updated): {processed_count}")
    print(f"Skipped files (precedent not found in DB): {precedent_not_found_count}")
    print(f"New relations created: {created_count}")
    print(f"Existing relations updated: {updated_count}")
    print("---------------------------------")

if __name__ == '__main__':
    populate_relations()
