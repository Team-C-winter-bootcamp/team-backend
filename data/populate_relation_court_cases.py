import os
import django
import json
import glob
import re
import sys

# Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import Precedent, ReferenceCourtCase, RelationCourtCase
from django.db import connection

# 이 함수는 populate_reference_court_cases.py 에서 복사해왔습니다.
def parse_ref_case_nos(text):
    """
    "선고"와 "판결" 사이의 텍스트에서 유효한 사건번호들을 추출합니다.
    """
    if not text:
        return []

    final_nos = set()
    segments = re.findall(r'선고(.*?)판결', text)

    for segment in segments:
        clean_segment = re.sub(r'\(.*?\)|\[.*?\]|\【.*?\】|전원합의체|공\d+', '', segment)
        base_pattern = r'\d+(?:[가-힣]+|-)\d+'
        initial_matches = re.findall(base_pattern, clean_segment)
        for match in initial_matches:
            final_nos.add(match)

        parts = re.split(r'[\s,]+', clean_segment)
        last_prefix = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            if re.fullmatch(base_pattern, part):
                prefix_match = re.match(r'\d+[가-힣]+', part)
                if prefix_match:
                    last_prefix = prefix_match.group(0)
            elif re.fullmatch(r'\d+', part) and last_prefix:
                final_nos.add(last_prefix + part)

    return list(final_nos)

def populate_relation_court_cases():
    """
    JSON 원천 데이터를 기반으로 Precedent와 ReferenceCourtCase의 관계(M:N)를
    precedents_relationcourtcase 테이블에 채웁니다.
    """
    print("--- Starting to populate 'precedents_relationcourtcase' ---")

    # 1. 데이터베이스에서 ID 맵 미리 로드
    print("Step 1: Pre-loading Precedent and ReferenceCourtCase data into memory...")
    try:
        precedent_map = {p.case_no: p.id for p in Precedent.objects.all()}
        ref_case_map = {rc.ref_case_no: rc.id for rc in ReferenceCourtCase.objects.all()}
        print(f"  - Loaded {len(precedent_map)} precedents and {len(ref_case_map)} reference cases.")
    except Exception as e:
        print(f"  - FATAL ERROR loading data: {e}")
        return

    # 2. JSON 파일 목록 수집
    print("\nStep 2: Globbing for all source JSON files...")
    json_files = []
    base_paths = [
        '1.데이터/Training/01.원천데이터/**/*.json',
        '1.데이터/Validation/01.원천데이터/**/*.json'
    ]
    for path in base_paths:
        json_files.extend(glob.glob(path, recursive=True))
    
    if not json_files:
        print("  - ERROR: No JSON files found in source directories.")
        return
    print(f"  - Found a total of {len(json_files)} JSON files.")

    # 3. 관계 데이터 추출
    print("\nStep 3: Processing JSON files to build relations...")
    relations_to_create = set()
    skipped_files = 0
    total_files = len(json_files)

    for i, file_path in enumerate(json_files):
        progress = (i + 1) / total_files * 100
        sys.stdout.write(f"\r- Processing file {i+1}/{total_files} ({progress:.2f}%)")
        sys.stdout.flush()

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            main_case_no = data.get("사건번호")
            reference_text = data.get("참조판례")

            if not main_case_no or not reference_text:
                skipped_files += 1
                continue

            # main_case_no가 쉼표로 구분되어 있을 경우, 첫 번째 사건번호만 사용
            main_case_no_cleaned = main_case_no.split(',')[0].strip()
            
            precedent_id = precedent_map.get(main_case_no_cleaned)
            if not precedent_id:
                skipped_files += 1
                continue
            
            ref_case_nos = parse_ref_case_nos(reference_text)
            for ref_no in ref_case_nos:
                ref_id = ref_case_map.get(ref_no)
                if ref_id:
                    relations_to_create.add((precedent_id, ref_id))

        except Exception as e:
            print(f"\n  - WARNING: Could not process file {file_path}. Error: {e}")
            skipped_files += 1
    
    print(f"\n  - Done. Found {len(relations_to_create)} unique relations. Skipped {skipped_files} files.")

    # 4. 데이터베이스에 삽입
    print("\nStep 4: Populating the database...")

    print("  - Truncating 'precedents_relationcourtcase' table...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE precedents_relationcourtcase RESTART IDENTITY;")
        print("  - SUCCESS: Table truncated.")
    except Exception as e:
        print(f"  - FATAL ERROR during truncation: {e}")
        return

    if not relations_to_create:
        print("  - No new relations to insert.")
        print("\n--- Population process finished ---")
        return

    print(f"  - Inserting {len(relations_to_create)} new relations...")
    
    # bulk_create를 위한 객체 리스트 생성
    objects = [
        RelationCourtCase(precedent_id=p_id, reference_court_case_id=rc_id)
        for p_id, rc_id in relations_to_create
    ]

    try:
        RelationCourtCase.objects.bulk_create(objects, batch_size=500)
        print("  - SUCCESS: Bulk insert completed.")
    except Exception as e:
        print(f"  - FATAL ERROR during bulk insert: {e}")

    print("\n--- Population process finished ---")


if __name__ == "__main__":
    populate_relation_court_cases()
