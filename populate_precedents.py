import os
import json
import glob
import re
import sys
import django

# Django 환경 설정
# 'config.settings'는 프로젝트의 실제 설정 파일 경로에 맞게 조정해야 할 수 있습니다.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from precedents.models import Precedent, Court, SubCategory

def format_judge_date(date_str):
    """'YYYY. M. D.' 형식의 날짜 문자열을 'YYYY-MM-DD'로 변환합니다."""
    if not date_str:
        return None
    parts = re.findall(r'\d+', date_str)
    if len(parts) == 3:
        year, month, day = parts
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return None

def populate_data():
    """JSON 파일에서 데이터를 읽어 데이터베이스에 채웁니다."""
    try:
        # 1. ORM을 사용하여 외래 키 정보 로드
        court_map = {court.court_name.strip(): court.id for court in Court.objects.all()}
        subcategory_map = {sc.subcategory_name.strip(): sc.id for sc in SubCategory.objects.all()}
        print("외래 키 정보를 성공적으로 로드했습니다.")
        
        # 2. 처리할 JSON 파일 목록 생성
        json_files = []
        base_paths = [
            '1.데이터/Training/02.라벨링데이터/**/*.json',
            '1.데이터/Validation/02.라벨링데이터/**/*.json'
        ]
        for path in base_paths:
            json_files.extend(glob.glob(path, recursive=True))

        total_files = len(json_files)
        print(f"총 {total_files}개의 JSON 파일을 찾았습니다. 데이터 삽입을 준비합니다...")

        precedents_to_create = []
        skipped_count = 0
        skipped_files_details = [] 

        # 3. 각 JSON 파일을 순회하며 데이터 처리
        for i, file_path in enumerate(json_files):
            progress = (i + 1) / total_files * 100
            sys.stdout.write(f"\r- 진행률: {progress:.2f}% ({i + 1}/{total_files})")
            sys.stdout.flush()

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                info = data.get('info', {})
                class_info = data.get('Class_info', {})

                case_no = info.get('caseNo')
                court_nm = info.get('courtNm', '').strip()
                case_title = info.get('caseTitle')
                case_nm = info.get('caseNm')
                court_type = info.get('courtType')
                judge_date_str = info.get('judmnAdjuDe')
                instance_name = class_info.get('instance_name', '').strip()
                
                court_id = court_map.get(court_nm)
                subcategory_id = subcategory_map.get(instance_name)
                judge_date = format_judge_date(judge_date_str)

                # 필수 정보 누락 시 건너뛰기
                if not all([case_no, court_nm, case_title, case_nm, judge_date, court_id, subcategory_id]):
                    skipped_count += 1
                    reason = []
                    if not case_no: reason.append('case_no')
                    if not court_nm: reason.append('court_nm')
                    if not case_title: reason.append('case_title')
                    if not case_nm: reason.append('case_nm')
                    if not judge_date: reason.append('judge_date')
                    if court_id is None: reason.append(f'court_id (from {court_nm})')
                    if subcategory_id is None: reason.append(f'subcategory_id (from {instance_name})')
                    skipped_files_details.append(f"{os.path.basename(file_path)}: 필수 정보 누락 ({', '.join(reason)})")
                    continue

                # Precedent 인스턴스 생성 후 리스트에 추가
                precedent_obj = Precedent(
                    case_no=case_no.split(',')[0],
                    case_name=case_nm,
                    case_title=case_title,
                    decision_type=court_type,
                    judge_date=judge_date,
                    court_id=court_id,
                    subcategory_id=subcategory_id
                )
                precedents_to_create.append(precedent_obj)

            except json.JSONDecodeError as e:
                skipped_count += 1
                skipped_files_details.append(f"{os.path.basename(file_path)}: JSON 파싱 오류 - {e}")
            except Exception as e:
                skipped_count += 1
                skipped_files_details.append(f"{os.path.basename(file_path)}: 알 수 없는 오류 - {e}")
        
        sys.stdout.write("\n")

        # 4. bulk_create로 한 번에 데이터베이스에 삽입
        if precedents_to_create:
            print(f"\n총 {len(precedents_to_create)}개의 판례 데이터를 데이터베이스에 삽입합니다...")
            # ignore_conflicts=True는 case_no가 중복될 경우 무시하고 넘어가도록 합니다 (ON CONFLICT DO NOTHING).
            Precedent.objects.bulk_create(precedents_to_create, ignore_conflicts=True)
            inserted_count = len(precedents_to_create)
            print(f"총 {inserted_count}개의 데이터가 성공적으로 삽입 대상이 되었습니다.")
        else:
            inserted_count = 0
            print("\n삽입할 데이터가 없습니다.")

        print(f"총 {total_files}개 파일 중, {inserted_count}개 삽입 시도, {skipped_count}개 건너뜀.")

        if skipped_files_details:
            print("\n--- 건너뛴 파일 상세 정보 ---")
            for detail in skipped_files_details:
                print(f"  - {detail}")
            print("--- 상세 정보 끝 ---")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] 스크립트 실행 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    populate_data()