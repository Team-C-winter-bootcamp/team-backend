
import os
import django
import json
from pathlib import Path
import argparse
from django.db import connection

# Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import Category, SubCategory

# --- 설정 ---
# 데이터를 검색할 루트 폴더 목록
DATA_ROOTS = [
    Path("1.데이터/Training/02.라벨링데이터"),
    Path("1.데이터/Validation/02.라벨링데이터"), # 사용자가 명시한 경로 (오타일 수 있으나 그대로 사용)
]

def populate_subcategories_by_name():
    """
    precedents_subcategory 테이블을 JSON 파일의 class_name을 기준으로 채웁니다.
    기존 데이터를 삭제하고 새로 채웁니다.
    """
    print("--- Starting to populate 'precedents_subcategory' based on class_name ---")

    # 1. 외래 키가 될 Category 테이블 데이터 미리 로드 (이름 -> ID 맵)
    print("Step 1: Pre-loading 'precedents_category' data into memory...")
    try:
        category_map = {cat.category_name: cat.id for cat in Category.objects.all()}
        if not category_map:
            print("  - CRITICAL: 'precedents_category' table is empty. Please populate it first.")
            return
        print(f"  - Loaded {len(category_map)} categories.")
    except Exception as e:
        print(f"  - FATAL ERROR loading category data: {e}")
        return

    # 2. 모든 JSON 파일 경로 수집
    print("\nStep 2: Globbing for all JSON files...")
    json_files = []
    for root in DATA_ROOTS:
        if root.exists():
            json_files.extend(root.rglob("*.json"))
        else:
            print(f"  - WARNING: Directory not found, skipping: {root}")
    
    if not json_files:
        print("  - ERROR: No JSON files found in any specified directory.")
        return
    print(f"  - Found a total of {len(json_files)} JSON files.")

    # 3. 기존 SubCategory 데이터 및 관련 테이블 TRUNCATE
    print("\nStep 3: Truncating subcategory and dependent tables to reset PKs...")
    try:
        with connection.cursor() as cursor:
            cursor.execute("TRUNCATE TABLE precedents_subcategory RESTART IDENTITY CASCADE;")
        print("  - SUCCESS: Truncated 'precedents_subcategory' and dependent tables ('precedents_precedent'). PK sequence reset.")
    except Exception as e:
        print(f"  - FATAL ERROR during truncation: {e}")
        return


    # 4. JSON 파일을 순회하며 데이터 삽입
    print("\nStep 4: Processing JSON files and populating subcategories...")
    inserted_count = 0
    failed_count = 0
    # unique 한 (부모_ID, 서브카테고리_이름) 조합을 추적하기 위한 Set
    unique_subcategories = set()

    for file_path in json_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            class_info = data.get("Class_info", {})
            class_name = class_info.get("class_name")
            instance_name = class_info.get("instance_name")

            if not class_name or not instance_name:
                failed_count += 1
                continue

            # 맵에서 부모 카테고리 ID 조회
            parent_category_id = category_map.get(class_name)

            if parent_category_id is None:
                failed_count += 1
                continue
            
            # 중복 삽입 방지
            unique_key = (parent_category_id, instance_name)
            if unique_key in unique_subcategories:
                continue

            SubCategory.objects.create(
                category_id=parent_category_id,
                subcategory_name=instance_name
            )
            unique_subcategories.add(unique_key)
            inserted_count += 1

        except Exception:
            failed_count += 1
            
    print("\n  --- Subcategory population complete ---")
    print(f"  - Total Inserted: {inserted_count}")
    print(f"  - Total Failed (missing data, etc.): {failed_count}")
    print("\n--- Population process finished ---")


if __name__ == "__main__":
    populate_subcategories_by_name()
