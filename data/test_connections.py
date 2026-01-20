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
# 프로젝트 루트 디렉토리 (read me 폴더의 부모 디렉토리)
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
import django
django.setup()

from django.conf import settings
from django.db import connection
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import boto3
from botocore.exceptions import ClientError

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
                with default_storage.open(saved_path, 'r', encoding='utf-8') as f:
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
        
        # ========== S3 버킷 데이터 확인 ==========
        print("\n[3] S3 버킷 데이터 확인")
        print("-" * 70)
        
        try:
            # boto3 클라이언트 생성
            s3_client = boto3.client(
                's3',
                aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
                aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
                region_name=getattr(settings, 'AWS_S3_REGION_NAME', 'ap-northeast-2')
            )
            
            bucket_name = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', None)
            print(f"  버킷 이름: {bucket_name}")
            
            # 버킷의 모든 객체 목록 가져오기
            print("  [조회 중] S3 버킷의 파일 목록을 가져오는 중...")
            
            all_objects = []
            paginator = s3_client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    all_objects.extend(page['Contents'])
            
            total_count = len(all_objects)
            total_size = sum(obj.get('Size', 0) for obj in all_objects)
            
            print(f"  [결과] 총 파일 개수: {total_count}개")
            print(f"  [결과] 총 용량: {total_size / (1024*1024):.2f} MB")
            
            if total_count > 0:
                print(f"\n  [파일 목록] (최대 20개 표시)")
                print("  " + "-" * 68)
                
                # 최신 파일부터 정렬
                sorted_objects = sorted(all_objects, key=lambda x: x.get('LastModified', ''), reverse=True)
                
                for idx, obj in enumerate(sorted_objects[:20], 1):
                    key = obj.get('Key', '')
                    size = obj.get('Size', 0)
                    last_modified = obj.get('LastModified', '')
                    
                    size_str = f"{size / 1024:.2f} KB" if size < 1024*1024 else f"{size / (1024*1024):.2f} MB"
                    
                    print(f"  {idx:2d}. {key[:60]:<60} | {size_str:>10} | {last_modified.strftime('%Y-%m-%d %H:%M:%S') if hasattr(last_modified, 'strftime') else last_modified}")
                
                if total_count > 20:
                    print(f"  ... 외 {total_count - 20}개 파일 더 있음")
                
                # 디렉토리별 파일 개수 통계
                print(f"\n  [디렉토리별 통계]")
                dir_stats = {}
                for obj in all_objects:
                    key = obj.get('Key', '')
                    if '/' in key:
                        dir_name = key.split('/')[0]
                        dir_stats[dir_name] = dir_stats.get(dir_name, 0) + 1
                    else:
                        dir_stats['(루트)'] = dir_stats.get('(루트)', 0) + 1
                
                for dir_name, count in sorted(dir_stats.items(), key=lambda x: x[1], reverse=True):
                    print(f"    {dir_name}: {count}개")
            else:
                print("  [안내] S3 버킷에 파일이 없습니다.")
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == 'NoSuchBucket':
                print(f"  [오류] 버킷이 존재하지 않습니다: {bucket_name}")
            elif error_code == 'AccessDenied':
                print(f"  [오류] 버킷 접근 권한이 없습니다")
            else:
                print(f"  [오류] S3 데이터 조회 실패: {e}")
        except Exception as e:
            print(f"  [오류] S3 데이터 조회 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
        
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
