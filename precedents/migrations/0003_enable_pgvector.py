# precedents/migrations/0003_enable_pgvector.py

from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        # 중요! 방금 보여주신 0002번 파일 뒤에 줄을 서야 합니다.
        ('precedents', '0002_alter_relationoutcome_precedent'),
    ]

    operations = [
        # RDS(서버)나 로컬 DB에 'vector' 기능을 켜주는 명령어
        migrations.RunSQL(
            sql='CREATE EXTENSION IF NOT EXISTS vector;',
            reverse_sql='DROP EXTENSION IF EXISTS vector;'
        ),
    ]