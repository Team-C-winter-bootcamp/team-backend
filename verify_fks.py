import os
import django
from django.db.models import Count

# Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import SubCategory, Category

def verify_subcategory_fks():
    """
    precedents_subcategory 테이블의 category_id FK 분포를 확인하고 출력합니다.
    """
    print("--- Verifying Foreign Key distribution in 'precedents_subcategory' ---")

    distribution = SubCategory.objects.values('category_id').annotate(count=Count('id')).order_by('category_id')

    if not distribution:
        print("No subcategories found in the database.")
        return

    print("Distribution of subcategories per Category ID:")
    
    total_subcategories = 0
    category_map = {cat.id: cat.category_name for cat in Category.objects.all()}
    all_category_ids = set(category_map.keys())
    found_category_ids = set()

    for item in distribution:
        category_id = item['category_id']
        found_category_ids.add(category_id)
        count = item['count']
        category_name = category_map.get(category_id, "Unknown Category")
        print(f"  - Category ID: {category_id} ({category_name}) -> has {count} subcategories.")
        total_subcategories += count
        
    missing_ids = all_category_ids - found_category_ids
    if missing_ids:
        print("\n  - WARNING: Categories with NO subcategories:")
        for missing_id in sorted(list(missing_ids)):
            category_name = category_map.get(missing_id, "Unknown Category")
            print(f"    - Category ID: {missing_id} ({category_name})")


    print(f"\nTotal subcategories found: {total_subcategories}")
    print("--- Verification complete ---")


if __name__ == "__main__":
    verify_subcategory_fks()
