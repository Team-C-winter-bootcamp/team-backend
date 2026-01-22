"""
auth_user 테이블을 직접 생성하는 스크립트
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from django.db import connection
from django.core.management import sql

# auth_user 테이블 생성 SQL 가져오기
from django.contrib.auth import models as auth_models

cursor = connection.cursor()

# auth_user 테이블이 이미 있는지 확인
try:
    cursor.execute("SELECT COUNT(*) FROM auth_user")
    print("auth_user 테이블이 이미 존재합니다.")
except Exception as e:
    print(f"auth_user 테이블이 없습니다. 생성합니다...")
    
    # Django의 SQL 생성 기능 사용
    from django.db import models
    from django.contrib.auth.models import User
    
    # User 모델의 테이블 생성 SQL 가져오기
    sql_statements = connection.ops.sql_create_table(
        User._meta.db_table,
        [
            models.AutoField(primary_key=True, name='id'),
            models.CharField(max_length=150, name='username', unique=True),
            models.CharField(max_length=150, name='first_name'),
            models.CharField(max_length=150, name='last_name'),
            models.EmailField(name='email'),
            models.BooleanField(default=True, name='is_staff'),
            models.BooleanField(default=True, name='is_active'),
            models.BooleanField(default=False, name='is_superuser'),
            models.DateTimeField(name='date_joined'),
            models.DateTimeField(null=True, blank=True, name='last_login'),
        ]
    )
    
    # 더 간단한 방법: Django의 migrate 명령을 사용하되, SQL을 직접 실행
    # auth.0001_initial 마이그레이션의 SQL을 직접 실행
    try:
        # auth_user 테이블 생성 SQL
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS auth_user (
            id SERIAL PRIMARY KEY,
            password VARCHAR(128) NOT NULL,
            last_login TIMESTAMP NULL,
            is_superuser BOOLEAN NOT NULL,
            username VARCHAR(150) NOT NULL UNIQUE,
            first_name VARCHAR(150) NOT NULL,
            last_name VARCHAR(150) NOT NULL,
            email VARCHAR(254) NOT NULL,
            is_staff BOOLEAN NOT NULL,
            is_active BOOLEAN NOT NULL,
            date_joined TIMESTAMP NOT NULL
        );
        """
        cursor.execute(create_table_sql)
        print("auth_user 테이블이 성공적으로 생성되었습니다.")
    except Exception as e:
        print(f"테이블 생성 중 오류 발생: {e}")
        print("\n대안: RDS에 직접 접근하여 다음 SQL을 실행하세요:")
        print(create_table_sql)
