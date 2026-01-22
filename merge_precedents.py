import json
from pathlib import Path
import sys

# Python이 UTF-8 인코딩을 사용하도록 설정
sys.stdout.reconfigure(encoding='utf-8')

def merge_data():
    """
    라벨링데이터와 원천데이터의 JSON 파일들을 병합하여
    새로운 JSON 파일을 생성합니다.
    """
    # 현재 스크립트 파일의 위치를 기준으로 프로젝트 루트 경로를 설정
    project_root = Path(__file__).resolve().parent

    # 소스 및 대상 디렉토리 경로 정의
    label_data_path = project_root / "data_source/Training/02.라벨링데이터/TL_03.형사A(생활형)"
    source_data_path = project_root / "data_source/Training/01.원천데이터/TS_1.판례_03.형사A(생활형)"
    output_path = project_root / "data"

    # 출력 디렉토리가 없으면 생성
    output_path.mkdir(exist_ok=True)

    print(f"라벨링 데이터 폴더: {label_data_path}")
    print(f"원천 데이터 폴더: {source_data_path}")
    print(f"결과 저장 폴더: {output_path}")
    print("-" * 30)

    # 라벨링 데이터 폴더에 파일이 있는지 확인
    if not label_data_path.exists():
        print(f"오류: 라벨링 데이터 폴더를 찾을 수 없습니다: {label_data_path}")
        return

    # 처리할 파일 목록 가져오기
    label_files = list(label_data_path.glob("2023도*.json"))
    if not label_files:
        print("처리할 라벨링 데이터 파일이 없습니다. (2023도*.json)")
        return
        
    print(f"총 {len(label_files)}개의 라벨링 파일을 기준으로 병합을 시작합니다.")
    
    success_count = 0
    fail_count = 0

    for label_file_path in label_files:
        file_name = label_file_path.name
        source_file_path = source_data_path / file_name

        print(f"처리 중: {file_name} ... ", end="")

        if not source_file_path.exists():
            print("짝이 되는 원천 데이터 파일 없음. 건너뜁니다.")
            fail_count += 1
            continue

        try:
            # 두 개의 JSON 파일 읽기
            with open(label_file_path, 'r', encoding='utf-8') as f:
                label_data = json.load(f)
            
            with open(source_file_path, 'r', encoding='utf-8') as f:
                source_data = json.load(f)

            # 데이터 추출
            info = label_data.get("info", {})
            class_info = label_data.get("Class_info", {})
            
            merged_data = {
                "caseNo": info.get("caseNo"),
                "caseTitle": info.get("caseTitle"),
                "instance_name": class_info.get("instance_name"),
                "courtNm": info.get("courtNm"),
                "judmnAdjuDe": info.get("judmnAdjuDe"),
                "caseNm": info.get("caseNm"),
                "사건종류명": source_data.get("사건종류명"),
                "판례내용": source_data.get("판례내용")
            }

            # 누락된 필드가 있는지 확인 (선택적)
            if any(value is None for value in merged_data.values()):
                print(f"경고: 일부 필드가 누락되었습니다.")

            # 새로운 JSON 파일로 저장
            output_file_path = output_path / file_name
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
            print("병합 성공!")
            success_count += 1

        except json.JSONDecodeError as e:
            print(f"JSON 파싱 오류: {e}. 건너뜁니다.")
            fail_count += 1
        except Exception as e:
            print(f"알 수 없는 오류: {e}. 건너뜁니다.")
            fail_count += 1

    print("-" * 30)
    print(f"총 {len(label_files)}개 파일 중 {success_count}개 병합 성공, {fail_count}개 실패.")
    print(f"결과 파일은 '{output_path.relative_to(project_root)}' 폴더에 저장되었습니다.")


if __name__ == "__main__":
    merge_data()
