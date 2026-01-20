
import os
import django
from pathlib import Path
import re

# Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import Category

def temp_populate_categories():
    """
    지정된 폴더 이름에서 카테고리 이름을 추출하고, 순차적인 코드를 부여하여
    precedents_category 테이블을 채웁니다.
    """
    print("--- Starting temporary population of 'precedents_category' from new folder structure ---")

    # 1. 기존 카테고리 모두 삭제 (재설정 보장)
    print("Step 1: Deleting all existing categories to ensure a clean slate...")
    deleted_count, _ = Category.objects.all().delete()
    print(f"  - Deleted {deleted_count} existing category objects.")

    # 2. 새로운 카테고리 데이터 정의 (이전과 동일하지만 명시적으로 재확인)
    new_categories_data = [
        (1, "민사"),
        (2, "가사"),
        (3, "형사A(생활형)"),
        (4, "형사B(일반형)"),
        (5, "행정"),
        (6, "기업"),
        (7, "근로자"),
        (8, "특허.저작권"),
        (9, "금융조세"),
        (10, "개인정보.ICT"),
    ]

    print(f"\nStep 2: Populating 'precedents_category' table with {len(new_categories_data)} categories...")
    inserted_count = 0
    try:
        for code, name in new_categories_data:
            cat, created = Category.objects.get_or_create(
                category_code=code,
                defaults={'category_name': name}
            )
            if created:
                inserted_count += 1
        print(f"  - Inserted {inserted_count} new categories.")
    except Exception as e:
        print(f"  - FATAL ERROR during category population: {e}")
        return

    print("\n--- Temporary category population finished ---")

if __name__ == "__main__":
    temp_populate_categories()
