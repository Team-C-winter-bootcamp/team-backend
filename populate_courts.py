import os
import sys
import django
import glob
import json
from collections import defaultdict

# Django 환경 설정
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import Court

def get_court_type(court_name):
    """법원 이름에 따라 법원 종류를 반환합니다."""
    if '대법원' in court_name:
        return '대법원'
    if '고등법원' in court_name or '고법' in court_name:
        return '고등법원'
    if '지방법원' in court_name or '지법' in court_name:
        return '지방법원'
    if '가정법원' in court_name or '가법' in court_name:
        return '가정법원'
    if '특허법원' in court_name:
        return '특허법원'
    if '행정법원' in court_name:
        return '행정법원'
    if '회생법원' in court_name:
        return '회생법원'
    return '기타'

def get_court_code(court_name):
    """법원 이름에 맞는 법원 코드를 반환합니다. (일부 예시)"""
    codes = {
        '대법원': '100000',
        '서울고등법원': '100100',
        '대전고등법원': '100200',
        '대구고등법원': '100300',
        '부산고등법원': '100400',
        '광주고등법원': '100500',
        '수원고등법원': '100600',
        '특허법원': '100700',
        '서울중앙지방법원': '101101',
        '서울행정법원': '101102',
        '서울가정법원': '101103',
        '서울회생법원': '101104',
        '서울동부지방법원': '101201',
        '서울서부지방법원': '101301',
        '서울남부지방법원': '101401',
        '서울북부지방법원': '101501',
        # 필요에 따라 더 많은 법원 코드를 추가할 수 있습니다.
    }
    return codes.get(court_name, '000000') # 기본값

def populate_courts():
    """JSON 파일에서 법원 정보를 읽어와 데이터베이스에 저장합니다."""
    train_path = '1.데이터/Training/02.라벨링데이터/**/*.json'
    valid_path = '1.데이터/Validation/02.라벨링데이터/**/*.json'

    json_files = glob.glob(train_path, recursive=True) + glob.glob(valid_path, recursive=True)

    if not json_files:
        print("라벨링데이터 디렉터리에서 JSON 파일을 찾을 수 없습니다.")
        return

    total_files = len(json_files)
    print(f"총 {total_files}개의 JSON 파일을 처리합니다.")

    # 데이터베이스에 이미 있는 법원 이름 조회
    existing_courts = set(Court.objects.values_list('court_name', flat=True))
    print(f"데이터베이스에 이미 존재하는 법원 수: {len(existing_courts)}")

    new_courts_to_create = []
    found_court_names = set()
    processed_count = 0

    for file_path in json_files:
        processed_count += 1
        if processed_count % 1000 == 0:
            print(f"진행률: {processed_count}/{total_files} ({processed_count/total_files*100:.2f}%)")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # BUG FIX: Access courtNm from inside the 'info' object
                court_name = data.get('info', {}).get('courtNm')

                if court_name and court_name not in existing_courts and court_name not in found_court_names:
                    court_type = get_court_type(court_name)
                    court_code = get_court_code(court_name)
                    
                    new_courts_to_create.append(
                        Court(
                            court_name=court_name,
                            court_type=court_type,
                            court_code=court_code
                        )
                    )
                    found_court_names.add(court_name)
        
        except json.JSONDecodeError:
            print(f"JSON 파싱 오류: {file_path}")
        except Exception as e:
            print(f"파일 처리 중 오류 발생 {file_path}: {e}")

    # Print a summary of found courts
    if found_court_names:
        print(f"\n파일에서 총 {len(found_court_names)}개의 고유한 법원 이름을 찾았습니다.")
        # Print first 5 found courts as a sample
        print("샘플:", list(found_court_names)[:5])

    if new_courts_to_create:
        print(f"\n총 {len(new_courts_to_create)}개의 새로운 법원을 데이터베이스에 추가합니다.")
        Court.objects.bulk_create(new_courts_to_create)
        print("데이터 추가 완료.")
    else:
        print("\n추가할 새로운 법원이 없습니다.")

if __name__ == '__main__':
    populate_courts()
