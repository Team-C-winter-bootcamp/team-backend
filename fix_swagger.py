"""
Swagger ERR_EMPTY_RESPONSE 문제 해결 스크립트
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.conf import settings
from django.db import connection

print("=" * 50)
print("Swagger ERR_EMPTY_RESPONSE Fix")
print("=" * 50)

# 1. 데이터베이스 연결 확인
print("\n1. Database Connection Check:")
try:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
    print("[OK] Database connection successful")
except Exception as e:
    print(f"[ERROR] Database connection failed: {e}")
    print("\nPossible solutions:")
    print("  - Check DB_HOST, DB_NAME, DB_USER, DB_PASSWORD in backend.env")
    print("  - If using RDS, verify the endpoint is correct")
    print("  - If using local PostgreSQL, ensure it's running")
    print("  - Try switching to SQLite: Set DB_ENGINE=sqlite3 in backend.env")

# 2. 서버 포트 확인
print("\n2. Port 8000 Status:")
import subprocess
result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
if ':8000' in result.stdout:
    print("[WARNING] Port 8000 is in use")
    print("  Multiple server instances may be running")
    print("  Solution: Kill existing processes and restart server")
else:
    print("[OK] Port 8000 is available")

# 3. 설정 확인
print("\n3. Settings Check:")
print(f"  DEBUG: {settings.DEBUG}")
print(f"  ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
print(f"  Database: {settings.DATABASES['default']['ENGINE']}")

# 4. 해결 방법 제시
print("\n" + "=" * 50)
print("Recommended Solutions:")
print("=" * 50)
print("\n1. Kill existing server processes:")
print("   taskkill /F /PID <PID>  # Replace <PID> with process ID from netstat")
print("\n2. Restart server:")
print("   python manage.py runserver")
print("\n3. If database connection fails, use SQLite:")
print("   - Edit backend.env")
print("   - Set DB_ENGINE=sqlite3")
print("   - Restart server")
print("\n4. Check server logs for errors:")
print("   - Look for database connection errors")
print("   - Look for import errors")
print("   - Look for middleware errors")
