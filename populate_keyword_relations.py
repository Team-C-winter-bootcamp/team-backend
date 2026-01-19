import os
import json
import glob
import sys
import django
from django.db import transaction

# Django 환경 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from precedents.models import Precedent, Keyword, RelationKeyword

def populate_relations():
    """
    JSON 파일에서 판례와 키워드 관계를 읽어
    RelationKeyword 테이블에 채웁니다.
    """
    try:
        print("기존 관계 데이터 삭제 중...")
        RelationKeyword.objects.all().delete()
        
        print("데이터베이스에서 판례와 키워드 정보를 불러오는 중...")
        precedent_map = {p.case_no: p.id for p in Precedent.objects.all()}
        keyword_map = {k.name: k.id for k in Keyword.objects.all()}
        print(f"판례 {len(precedent_map)}개, 키워드 {len(keyword_map)}개를 불러왔습니다.")

        json_files = []
        base_paths = [
            '1.데이터/Training/02.라벨링데이터/**/*.json',
            '1.데이터/Validation/02.라벨링데이터/**/*.json'
        ]
        for path in base_paths:
            json_files.extend(glob.glob(path, recursive=True))

        total_files = len(json_files)
        print(f"총 {total_files}개의 JSON 파일을 찾았습니다. 관계 생성을 시작합니다...")

        relations_to_create = []
        processed_files = 0
        for file_path in json_files:
            processed_files += 1
            progress = (processed_files / total_files) * 100
            sys.stdout.write(f"\r- 파일 처리 진행률: {progress:.2f}% ({processed_files}/{total_files})")
            sys.stdout.flush()

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 사건 번호 추출 (쉼표 앞부분만)
                case_no = data.get('info', {}).get('caseNo', '').split(',')[0].strip()
                if not case_no:
                    continue

                precedent_id = precedent_map.get(case_no)
                if not precedent_id:
                    continue
                
                # 키워드 추출 (다양한 JSON 구조에 대응)
                keyword_tags = data.get('keyword_tagg')
                if keyword_tags is None:
                    labeled_data = data.get('labeled_data', {})
                    keyword_tags = labeled_data.get('keyword_tagg', [])

                if isinstance(keyword_tags, list):
                    for tag in keyword_tags:
                        if isinstance(tag, dict):
                            keyword_name = tag.get('keyword')
                        elif isinstance(tag, str):
                            keyword_name = tag
                        else:
                            keyword_name = None

                        if keyword_name:
                            keyword_id = keyword_map.get(keyword_name.strip())
                            if keyword_id:
                                relations_to_create.append(
                                    RelationKeyword(precedent_id=precedent_id, keyword_id=keyword_id)
                                )

            except (json.JSONDecodeError, KeyError) as e:
                # print(f"\n파일 처리 중 오류: {file_path} - {e}")
                continue
        
        sys.stdout.write("\n")
        print(f"총 {len(relations_to_create)}개의 관계를 생성할 준비가 되었습니다.")

        if relations_to_create:
            print("데이터베이스에 관계 정보 삽입을 시작합니다...")
            with transaction.atomic():
                RelationKeyword.objects.bulk_create(relations_to_create, ignore_conflicts=True)
            print(f"{len(relations_to_create)}개의 관계 정보를 성공적으로 삽입했습니다.")
        else:
            print("새로 추가할 관계 정보가 없습니다.")

    except Exception as e:
        print(f"\n[CRITICAL ERROR] 스크립트 실행 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    populate_relations()
