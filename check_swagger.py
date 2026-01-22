"""
Swagger 접속 문제 진단 스크립트
"""
import os
import sys
import django

# Django 설정
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.conf import settings
from django.urls import reverse, NoReverseMatch
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

print("=" * 50)
print("Swagger Diagnosis")
print("=" * 50)

# 1. drf-yasg 설치 확인
try:
    import drf_yasg
    print(f"[OK] drf-yasg installed: {drf_yasg.__version__}")
except ImportError:
    print("[ERROR] drf-yasg is not installed.")
    print("   Install: pip install drf-yasg")
    sys.exit(1)

# 2. INSTALLED_APPS 확인
if 'drf_yasg' in settings.INSTALLED_APPS:
    print("[OK] drf-yasg is in INSTALLED_APPS")
else:
    print("[ERROR] drf-yasg is not in INSTALLED_APPS")

# 3. DEBUG 모드 확인
print(f"DEBUG mode: {settings.DEBUG}")
print(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")

# 4. URL 패턴 확인
from django.urls import get_resolver
resolver = get_resolver()

swagger_urls = []
for pattern in resolver.url_patterns:
    if hasattr(pattern, 'name') and pattern.name:
        if 'swagger' in pattern.name.lower() or 'schema' in pattern.name.lower():
            swagger_urls.append(pattern.name)

if swagger_urls:
    print(f"[OK] Swagger URL patterns found: {swagger_urls}")
    
    # URL 역방향 확인
    try:
        swagger_url = reverse('schema-swagger-ui')
        print(f"[OK] Swagger UI URL: {swagger_url}")
    except NoReverseMatch as e:
        print(f"[ERROR] Swagger UI URL reverse failed: {e}")
    
    try:
        swagger_json_url = reverse('schema-json', kwargs={'format': '.json'})
        print(f"[OK] Swagger JSON URL: {swagger_json_url}")
    except NoReverseMatch as e:
        print(f"[ERROR] Swagger JSON URL reverse failed: {e}")
else:
    print("[ERROR] Swagger URL patterns not found")

# 5. schema_view 생성 확인
try:
    schema_view = get_schema_view(
        openapi.Info(
            title="Team Backend API",
            default_version='v1',
            description="Team Backend API",
        ),
        public=True,
    )
    print("[OK] schema_view created successfully")
except Exception as e:
    print(f"[ERROR] schema_view creation failed: {e}")

# 6. 정적 파일 설정 확인
print(f"\nStatic files settings:")
print(f"  STATIC_URL: {settings.STATIC_URL}")
print(f"  STATIC_ROOT: {settings.STATIC_ROOT}")

# 7. 미들웨어 확인
if 'django.middleware.csrf.CsrfViewMiddleware' in settings.MIDDLEWARE:
    print("[WARNING] CSRF middleware is enabled. Swagger may need CSRF token.")

print("\n" + "=" * 50)
print("Diagnosis Complete")
print("=" * 50)
print("\nSwagger URLs:")
print("  - Swagger UI: http://localhost:8000/swagger/")
print("  - ReDoc: http://localhost:8000/redoc/")
print("  - JSON: http://localhost:8000/swagger.json")
print("\nTo start server: python manage.py runserver")
