
import os
import django

# Django 환경 설정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import Category

def update_category_name_id8():
    """
    precedents_category 테이블에서 ID가 8인 카테고리의 이름을 '특허/저작권'으로 업데이트합니다.
    """
    print("--- Starting update of category name for ID 8 ---")

    try:
        category_to_update = Category.objects.get(id=8)
        old_name = category_to_update.category_name
        new_name = "특허/저작권"
        category_to_update.category_name = new_name
        category_to_update.save()
        print(f"  - SUCCESS: Updated Category ID 8 name from '{old_name}' to '{new_name}'.")
    except Category.DoesNotExist:
        print("  - ERROR: Category with ID 8 not found.")
    except Exception as e:
        print(f"  - FATAL ERROR during update: {e}")

    print("\n--- Update process finished ---")

if __name__ == "__main__":
    update_category_name_id8()
