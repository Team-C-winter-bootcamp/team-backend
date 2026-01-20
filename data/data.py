import os
import json
from pathlib import Path
from datetime import datetime

import django

#  settings 확정
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from precedents.models import Precedent


BASE_DATA_DIR = Path(__file__).resolve().parent / "data" / "aihub" / "TS_1.판례_01.민사"
json_files = sorted(BASE_DATA_DIR.rglob("*.json"))

print("BASE_DATA_DIR =", BASE_DATA_DIR)
print("JSON files =", len(json_files))

if not json_files:
    raise SystemExit(' JSON 파일을 못 찾음. 경로 확인 필요')


def parse_date(s: str):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def to_int(value):
    """94224 / 94224.0 / '94224' / '94224.0' 다 커버"""
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        try:
            return int(float(value))
        except Exception:
            return None


inserted = 0
skipped = 0
failed = 0

for i, fp in enumerate(json_files, start=1):
    try:
        with open(fp, "r", encoding="utf-8") as f:
            row = json.load(f)

        pid = to_int(row.get("판례일련번호"))
        if not pid:
            skipped += 1
            continue

        _, created = Precedent.objects.get_or_create(
            precedent_id=pid,
            defaults={
                "case_name": row.get("사건명"),
                "case_number": row.get("사건번호"),
                "decision_date": parse_date(row.get("선고일자")),
                "court_name": row.get("법원명"),
                "case_type_name": row.get("사건종류명"),
                "judgment_type": row.get("판결유형"),
                "decision": row.get("선고"),
                "detail_link": row.get("판례상세링크"),
                "issue": row.get("판시사항"),
                "summary": row.get("판결요지"),
                "content": row.get("판례내용"),
                "raw_json": row,
            },
        )

        if created:
            inserted += 1
        else:
            skipped += 1

        #  진행 로그 (500건마다)
        if i % 500 == 0:
            print(f"[{i}/{len(json_files)}] inserted={inserted}, skipped={skipped}, failed={failed}")

    except Exception as e:
        failed += 1
        print(f'failed file={fp} err={e}')

print(f" DONE inserted={inserted}, skipped={skipped}, failed={failed}")
