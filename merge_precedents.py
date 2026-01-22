"""
원천데이터와 라벨링데이터를 병합하는 스크립트

원천데이터에서 추출: 판시사항, 판결요지, 판례내용
라벨링데이터에서 추출: caseNm, caseTitle, courtNm, judmnAdjuDe, caseNo, jdgmn, Summary, keyword_tagg, Reference_info, Class_info
"""
import json
import os
from pathlib import Path
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 경로 설정
BASE_DIR = Path(__file__).parent
SOURCE_DATA_DIR = BASE_DIR / "data" / "원천데이터"
LABELED_DATA_DIR = BASE_DIR / "data" / "라벨링데이터"
MERGED_DATA_DIR = BASE_DIR / "data" / "merged"


def merge_precedents():
    """원천데이터와 라벨링데이터를 병합합니다."""
    # merged 폴더가 없으면 생성
    MERGED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    # 원천데이터 폴더 확인
    if not SOURCE_DATA_DIR.exists():
        logging.error(f"원천데이터 폴더가 없습니다: {SOURCE_DATA_DIR}")
        return
    
    # 라벨링데이터 폴더 확인
    if not LABELED_DATA_DIR.exists():
        logging.error(f"라벨링데이터 폴더가 없습니다: {LABELED_DATA_DIR}")
        return
    
    # 원천데이터와 라벨링데이터의 JSON 파일 목록 가져오기
    source_files = {f.stem: f for f in SOURCE_DATA_DIR.glob("*.json")}
    labeled_files = {f.stem: f for f in LABELED_DATA_DIR.glob("*.json")}
    
    # 공통 파일명 찾기
    common_files = set(source_files.keys()) & set(labeled_files.keys())
    
    if not common_files:
        logging.warning("원천데이터와 라벨링데이터에 공통된 파일이 없습니다.")
        return
    
    logging.info(f"총 {len(common_files)}개의 파일을 병합합니다.")
    
    merged_count = 0
    error_count = 0
    
    for file_stem in common_files:
        source_file = source_files[file_stem]
        labeled_file = labeled_files[file_stem]
        
        try:
            # 원천데이터 읽기
            with open(source_file, 'r', encoding='utf-8') as f:
                source_data = json.load(f)
            
            # 라벨링데이터 읽기
            with open(labeled_file, 'r', encoding='utf-8') as f:
                labeled_data = json.load(f)
            
            # 병합된 데이터 생성
            merged_data = {}
            
            # 원천데이터에서 추출할 필드
            if "판시사항" in source_data:
                merged_data["판시사항"] = source_data["판시사항"]
            if "판결요지" in source_data:
                merged_data["판결요지"] = source_data["판결요지"]
            if "판례내용" in source_data:
                merged_data["판례내용"] = source_data["판례내용"]
            
            # 판례일련번호 (원천데이터에서)
            if "판례일련번호" in source_data:
                merged_data["판례일련번호"] = source_data["판례일련번호"]
            
            # 라벨링데이터에서 추출할 필드
            if "info" in labeled_data:
                info = labeled_data["info"]
                merged_data["caseNm"] = info.get("caseNm", "")
                merged_data["caseTitle"] = info.get("caseTitle", "")
                merged_data["courtNm"] = info.get("courtNm", "")
                merged_data["judmnAdjuDe"] = info.get("judmnAdjuDe", "")
                merged_data["caseNo"] = info.get("caseNo", "")
            
            # jdgmn (라벨링데이터에서)
            if "jdgmn" in labeled_data:
                merged_data["jdgmn"] = labeled_data["jdgmn"]
            
            # Summary (라벨링데이터에서)
            if "Summary" in labeled_data:
                merged_data["Summary"] = labeled_data["Summary"]
            
            # keyword_tagg (라벨링데이터에서)
            if "keyword_tagg" in labeled_data:
                merged_data["keyword_tagg"] = labeled_data["keyword_tagg"]
            
            # Reference_info (라벨링데이터에서)
            if "Reference_info" in labeled_data:
                merged_data["Reference_info"] = labeled_data["Reference_info"]
            
            # Class_info (라벨링데이터에서)
            if "Class_info" in labeled_data:
                merged_data["Class_info"] = labeled_data["Class_info"]
            
            # 병합된 데이터 저장
            output_file = MERGED_DATA_DIR / f"{file_stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
            merged_count += 1
            logging.info(f"병합 완료: {file_stem}.json")
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON 파싱 오류 ({file_stem}): {e}")
            error_count += 1
        except Exception as e:
            logging.error(f"파일 처리 중 오류 발생 ({file_stem}): {e}")
            error_count += 1
    
    # 결과 요약
    logging.info("=" * 50)
    logging.info("병합 작업 완료")
    logging.info(f"  - 병합된 파일: {merged_count}개")
    logging.info(f"  - 오류: {error_count}개")
    logging.info(f"  - 출력 폴더: {MERGED_DATA_DIR}")


if __name__ == "__main__":
    try:
        logging.info("원천데이터와 라벨링데이터 병합 스크립트를 시작합니다.")
        merge_precedents()
        logging.info("모든 병합 작업이 완료되었습니다.")
    except KeyboardInterrupt:
        logging.info("\n사용자에 의해 중단되었습니다.")
    except Exception as e:
        logging.error(f"예기치 않은 오류 발생: {e}", exc_info=True)
        exit(1)
