"""
S3와 RDS 연결 확인용 스크립트
"""
import os
import sys
from pathlib import Path
from datetime import datetime

# Windows에서 UTF-8 인코딩 설정
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Django 설정
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django
django.setup()

from django.conf import settings
from django.db import connection
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

print("=" * 70)
print("S3 및 RDS 연결 종합 테스트")
print("=" * 70)

# ========== RDS 연결 테스트 ==========
print("\n[1] RDS 연결 테스트")
print("-" * 70)

try:
    db_config = settings.DATABASES['default']
    print(f"  Database: {db_config.get('NAME')}")
    print(f"  Host: {db_config.get('HOST')}")
    print(f"  User: {db_config.get('USER')}")
    print(f"  Port: {db_config.get('PORT')}")
    
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"  [성공] RDS 연결 성공!")
        print(f"  PostgreSQL 버전: {version[:60]}...")
        
        # 테이블 개수 확인
        cursor.execute("""
            SELECT COUNT(*) 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        table_count = cursor.fetchone()[0]
        print(f"  테이블 개수: {table_count}개")
        
        rds_ok = True
        
except Exception as e:
    print(f"  [실패] RDS 연결 실패: {e}")
    import traceback
    traceback.print_exc()
    rds_ok = False

# ========== S3 연결 테스트 ==========
print("\n[2] S3 연결 테스트")
print("-" * 70)

USE_S3 = getattr(settings, 'USE_S3', False)
print(f"  USE_S3: {USE_S3}")

if not USE_S3:
    print("  [건너뜀] USE_S3가 False로 설정되어 있습니다")
    print("  [안내] backend.env 파일에 다음 설정을 추가하세요:")
    print("    USE_S3=True")
    print("    AWS_ACCESS_KEY_ID=your-access-key")
    print("    AWS_SECRET_ACCESS_KEY=your-secret-key")
    print("    AWS_STORAGE_BUCKET_NAME=your-bucket-name")
    print("    AWS_S3_REGION_NAME=ap-northeast-2")
    s3_ok = None
else:
    try:
        # S3 설정 정보 출력
        print(f"  BUCKET: {getattr(settings, 'AWS_STORAGE_BUCKET_NAME', 'Not set')}")
        print(f"  REGION: {getattr(settings, 'AWS_S3_REGION_NAME', 'Not set')}")
        print(f"  ACCESS_KEY_ID: {getattr(settings, 'AWS_ACCESS_KEY_ID', 'Not set')[:10]}..." if getattr(settings, 'AWS_ACCESS_KEY_ID', None) else "  ACCESS_KEY_ID: Not set")
        
        # 파일 업로드 테스트
        test_content = f"S3 연결 테스트\n시간: {datetime.now()}\n테스트 성공!".encode('utf-8')
        test_file = ContentFile(test_content)
        test_path = f"test/connection_test_{int(datetime.now().timestamp())}.txt"
        
        print(f"  [업로드 시도] {test_path}")
        saved_path = default_storage.save(test_path, test_file)
        print(f"  [성공] 파일 업로드 완료: {saved_path}")
        
        # 파일 URL 확인
        try:
            file_url = default_storage.url(saved_path)
            print(f"  [URL] {file_url}")
        except Exception as e:
            print(f"  [URL 생성 실패] {e} (private 파일이므로 정상일 수 있습니다)")
        
        # 파일 존재 확인
        if default_storage.exists(saved_path):
            print(f"  [확인] 파일이 S3에 존재합니다")
            
            # 파일 읽기 테스트
            try:
                with default_storage.open(saved_path, 'r') as f:
                    content = f.read()
                    print(f"  [읽기 성공] 파일 내용: {content[:50]}...")
            except Exception as e:
                print(f"  [읽기 실패] {e}")
            
            # 테스트 파일 삭제
            try:
                default_storage.delete(saved_path)
                print(f"  [완료] 테스트 파일 삭제됨")
            except Exception as e:
                print(f"  [삭제 실패] {e} (수동으로 삭제해주세요)")
        
        s3_ok = True
        
    except Exception as e:
        print(f"  [실패] S3 연결 실패: {e}")
        import traceback
        traceback.print_exc()
        s3_ok = False

# ========== 결과 요약 ==========
print("\n" + "=" * 70)
print("[테스트 결과 요약]")
print("=" * 70)
print(f"  RDS 연결: {'✅ 성공' if rds_ok else '❌ 실패'}")
if s3_ok is not None:
    print(f"  S3 연결: {'✅ 성공' if s3_ok else '❌ 실패'}")
else:
    print(f"  S3 연결: ⚠️  비활성화됨 (USE_S3=False)")

if rds_ok and (s3_ok is None or s3_ok):
    print("\n[✅ 성공] 모든 연결 테스트 통과!")
    sys.exit(0)
else:
    print("\n[❌ 실패] 일부 연결 테스트 실패")
    sys.exit(1)
