import os
import django
import json
import glob
import re
import sys

# Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import ReferenceCourtCase
from django.db import connection

def parse_ref_case_nos(text):
    """
    "선고"와 "판결" 사이의 텍스트에서 유효한 사건번호들을 추출합니다.
    - '숫자+한글+숫자' 또는 '숫자-숫자' 형식의 사건번호를 인식합니다.
    - '2010두27639 2010두27646' 처럼 공백으로 분리된 여러 사건번호를 처리합니다.
    - '81다100681다카558' 처럼 붙어있는 사건번호를 분리합니다.
    - '2009다71312 71329 71336' 처럼 후속 번호만 나열된 경우를 처리합니다.
    - (공1982812), 전원합의체 등의 부가 정보는 제거합니다.
    """
    if not text:
        return []

    final_nos = set()
    
    # 1. "선고"와 "판결" 사이의 모든 텍스트 영역을 추출합니다.
    segments = re.findall(r'선고(.*?)판결', text)

    # 2. 각 텍스트 영역을 처리합니다.
    for segment in segments:
        # 괄호, '전원합의체' 등 불필요한 부분 제거 (괄호 수정 및 이스케이프)
        clean_segment = re.sub(r'\(.*?\)|\[.*?\]|\【.*?\】|전원합의체|공\d+', '', segment)
        
        # 3. 붙어있는 사건번호나 공백으로 분리된 사건번호를 먼저 모두 추출
        base_pattern = r'\d+(?:[가-힣]+|-)\d+'
        initial_matches = re.findall(base_pattern, clean_segment)
        for match in initial_matches:
            final_nos.add(match)

        # 4. 후속 번호 케이스 ('2009다71312 71329 ...') 처리
        parts = re.split(r'[\s,]+', clean_segment)
        last_prefix = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 완전한 사건번호 형식과 일치하는 경우
            if re.fullmatch(base_pattern, part):
                # final_nos에 이미 추가되었을 수 있으므로, 여기선 prefix만 업데이트
                prefix_match = re.match(r'\d+[가-힣]+', part)
                if prefix_match:
                    last_prefix = prefix_match.group(0)
            # 숫자만 있는 경우 (후속 번호로 간주)
            elif re.fullmatch(r'\d+', part) and last_prefix:
                # 마지막으로 찾은 prefix와 결합
                final_nos.add(last_prefix + part)

    # 5. 최종 결과 반환
    return list(final_nos)

def populate_reference_court_cases():
    """
    JSON 원천 데이터에서 '참조판례'를 파싱하여 precedents_referencecourtcase 테이블을 채웁니다.
    """
    print("--- Starting to populate 'precedents_referencecourtcase' ---")

    # 1. JSON 파일 목록 수집
    print("Step 1: Globbing for all source JSON files...")
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

    # 2. 모든 참조판례 번호 파싱 및 수집 (중복 제거)
    print("\nStep 2: Parsing all unique reference case numbers...")
    unique_ref_case_nos = set()
    total_files = len(json_files)
    processed_count = 0
    
    for i, file_path in enumerate(json_files):
        progress = (i + 1) / total_files * 100
        sys.stdout.write(f"\r- Processing file {i+1}/{total_files} ({progress:.2f}%)")
        sys.stdout.flush()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            reference_text = data.get('참조판례')
            
            if reference_text:
                ref_case_nos = parse_ref_case_nos(reference_text)
                if ref_case_nos:
                    unique_ref_case_nos.update(ref_case_nos)

            processed_count += 1
        except Exception as e:
            print(f"\n  - WARNING: Could not process file {file_path}. Error: {type(e).__name__}: {e}")

    print(f"\n  - Done. Found {len(unique_ref_case_nos)} unique reference case numbers from {processed_count} files.")

    # 3. 데이터베이스에 삽입
    print("\nStep 3: Populating the database...")
    
    print("  - Truncating 'precedents_referencecourtcase' table...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE precedents_referencecourtcase RESTART IDENTITY CASCADE;")
        print("  - SUCCESS: Table truncated.")
    except Exception as e:
        print(f"  - FATAL ERROR during truncation: {e}")
        return

    objects_to_create = [
        ReferenceCourtCase(ref_case_no=case_no)
        for case_no in unique_ref_case_nos
    ]

    if not objects_to_create:
        print("  - No new data to insert.")
        print("\n--- Population process finished ---")
        return

    try:
        print(f"  - Inserting {len(objects_to_create)} new reference court cases...")
        ReferenceCourtCase.objects.bulk_create(objects_to_create, batch_size=500)
        print("  - SUCCESS: Bulk insert completed.")
    except Exception as e:
        print(f"  - FATAL ERROR during bulk insert: {e}")

    print("\n--- Population process finished ---")


if __name__ == "__main__":
    populate_reference_court_cases()
