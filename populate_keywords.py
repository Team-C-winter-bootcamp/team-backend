import os
import json
import glob
import sys
import django

# Django 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from precedents.models import Keyword
from django.db import transaction

def populate_keywords():
    """JSON 파일에서 키워드 데이터를 읽어 데이터베이스에 채웁니다."""
    try:
        # 1. 처리할 JSON 파일 목록 생성
        json_files = []
        base_paths = [
            '1.데이터/Training/02.라벨링데이터/**/*.json',
            '1.데이터/Validation/02.라벨링데이터/**/*.json'
        ]
        for path in base_paths:
            json_files.extend(glob.glob(path, recursive=True))

        total_files = len(json_files)
        print(f"총 {total_files}개의 JSON 파일을 찾았습니다. 키워드 추출을 시작합니다...")

        # 2. 모든 JSON 파일에서 중복 없이 키워드 추출
        unique_keywords = set()
        for i, file_path in enumerate(json_files):
            progress = (i + 1) / total_files * 100
            sys.stdout.write(f"\r- 파일 처리 진행률: {progress:.2f}% ({i + 1}/{total_files})")
            sys.stdout.flush()

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 'keyword_tagg'는 'labeled_data' 안에 있거나 최상위 레벨에 있을 수 있습니다.
                # 먼저 최상위 레벨에서 찾아보고, 없으면 'labeled_data' 안에서 찾습니다.
                keyword_tags = data.get('keyword_tagg')
                if keyword_tags is None:
                    labeled_data = data.get('labeled_data', {})
                    keyword_tags = labeled_data.get('keyword_tagg', [])

                if isinstance(keyword_tags, list):
                    for tag in keyword_tags:
                        keyword = tag.get('keyword')
                        if keyword:
                            unique_keywords.add(keyword.strip())

            except json.JSONDecodeError:
                print(f"\n경고: {os.path.basename(file_path)} 파일은 JSON 형식이 아닙니다. 건너뜁니다.")
            except Exception as e:
                print(f"\n경고: {os.path.basename(file_path)} 처리 중 오류 발생 - {e}. 건너뜁니다.")
        
        sys.stdout.write("\n")
        print(f"총 {len(unique_keywords)}개의 고유한 키워드를 찾았습니다.")

        # 3. 데이터베이스에 이미 존재하는 키워드 조회
        existing_keywords = set(Keyword.objects.values_list('name', flat=True))
        print(f"데이터베이스에 이미 {len(existing_keywords)}개의 키워드가 존재합니다.")

        # 4. 새로운 키워드만 필터링
        new_keywords = unique_keywords - existing_keywords
        print(f"새로 추가할 키워드는 {len(new_keywords)}개입니다.")

        # 5. bulk_create로 새로운 키워드 한 번에 삽입
        if new_keywords:
            try:
                with transaction.atomic():
                    keywords_to_create = [Keyword(name=kw) for kw in new_keywords]
                    Keyword.objects.bulk_create(keywords_to_create)
                    print(f"{len(keywords_to_create)}개의 새로운 키워드를 데이터베이스에 성공적으로 삽입했습니다.")
            except Exception as e:
                print(f"\n[DB ERROR] 데이터베이스 삽입 중 오류 발생: {e}")
        else:
            print("새로 추가할 키워드가 없습니다.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] 스크립트 실행 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    populate_keywords()
