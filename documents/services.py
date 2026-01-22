import os
import re
import json
import google.generativeai as genai
from typing import Optional
from datetime import datetime

from .models import Template, Document
from .validators import validate_document


def initialize_gemini():
    """Gemini API 키를 환경 변수에서 읽어 초기화"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY 환경 변수가 설정되지 않았습니다.")
    genai.configure(api_key=api_key)


def get_active_template(doc_type: str) -> Optional[Template]:
    """
    주어진 doc_type에 대해 활성화된 최신 버전의 템플릿을 반환합니다.

    Args:
        doc_type: 문서 유형

    Returns:
        Template 객체 또는 None
    """
    return Template.objects.filter(
        doc_type=doc_type,
        is_active=True
    ).order_by('-version').first()


def build_gemini_prompt(template_content: str, variables: list, values: dict) -> str:
    """
    Gemini에 전달할 프롬프트를 생성합니다.

    Args:
        template_content: 템플릿 Markdown
        variables: 템플릿 변수 목록
        values: 사용자 입력 값

    Returns:
        Gemini 프롬프트 문자열
    """
    # 값이 없는 변수에 대해 UNKNOWN 기본값 설정
    filled_values = {}
    for var in variables:
        if var in values and values[var]:
            val = values[var]
            # 리스트인 경우 bullet point로 변환
            if isinstance(val, list):
                filled_values[var] = "\n".join(f"- {item}" for item in val)
            else:
                filled_values[var] = str(val)
        else:
            filled_values[var] = "UNKNOWN"

    prompt = f"""당신은 법률 문서 작성 전문가입니다. 아래 템플릿과 값을 사용하여 완성된 Markdown 문서를 생성해주세요.

## 절대 규칙 (반드시 준수)
1. 템플릿의 헤더(#, ##)와 섹션 제목을 절대 수정하지 마세요.
2. 템플릿에 없는 새로운 섹션이나 헤더를 추가하지 마세요.
3. 모든 {{{{...}}}} 플레이스홀더를 제공된 값으로 치환하세요.
4. 값이 없는 경우 "UNKNOWN"으로 채우세요.
5. 오직 완성된 Markdown 문서만 반환하세요. 설명이나 추가 텍스트는 포함하지 마세요.

## 템플릿
```markdown
{template_content}
```

## 변수 값
"""

    for var, val in filled_values.items():
        prompt += f"- {var}: {val}\n"

    prompt += """
## 출력
위 템플릿의 플레이스홀더를 값으로 치환한 완성된 Markdown 문서를 반환하세요.
코드 블록(```)이나 다른 마크업 없이 순수한 Markdown 문서만 반환하세요.
"""

    return prompt


def generate_document_with_gemini(template: Template, values: dict) -> str:
    """
    Gemini API를 사용하여 문서를 생성합니다.

    Args:
        template: Template 객체
        values: 변수 값 딕셔너리

    Returns:
        생성된 Markdown 문서
    """
    initialize_gemini()

    prompt = build_gemini_prompt(
        template_content=template.content_md,
        variables=template.variables,
        values=values
    )

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)

    generated_content = response.text.strip()

    # 코드 블록으로 감싸진 경우 제거
    if generated_content.startswith('```markdown'):
        generated_content = generated_content[11:]
    elif generated_content.startswith('```'):
        generated_content = generated_content[3:]

    if generated_content.endswith('```'):
        generated_content = generated_content[:-3]

    return generated_content.strip()


def extract_values_from_situation(situation_text: str, template: Template) -> dict:
    """
    사용자의 상황 설명 텍스트에서 템플릿에 필요한 값들을 추출합니다.

    Args:
        situation_text: 사용자가 자유롭게 작성한 상황 설명
        template: 대상 템플릿

    Returns:
        추출된 변수 값 딕셔너리
    """
    initialize_gemini()

    variables_desc = {
        "complainant_name": "고소인(피해자) 이름",
        "complainant_contact": "고소인 연락처 (전화번호)",
        "suspect_name": "피고소인(가해자/사기꾼) 이름",
        "suspect_contact": "피고소인 연락처 (전화번호, 계좌번호 등)",
        "incident_datetime": "사건 발생 일시",
        "incident_place": "사건 발생 장소 (온라인 플랫폼, 거래 방식 등)",
        "crime_facts": "범죄 사실 (구체적인 사기 내용)",
        "damage_amount": "피해 금액",
        "complaint_reason": "고소 이유 (왜 사기라고 생각하는지)",
        "evidence_list": "증거 자료 목록 (배열 형태)",
        "attachments": "첨부 자료 목록 (배열 형태)",
        "request_purpose": "고소 목적 (처벌, 환불 등)",
        "written_date": "작성일 (없으면 오늘 날짜)"
    }

    today = datetime.now().strftime("%Y-%m-%d")

    prompt = f"""당신은 법률 문서 작성을 위한 정보 추출 전문가입니다.

아래 사용자의 상황 설명에서 사기 고소장 작성에 필요한 정보를 추출해주세요.

## 사용자 상황 설명
{situation_text}

## 추출해야 할 정보
{json.dumps(variables_desc, ensure_ascii=False, indent=2)}

## 규칙
1. 텍스트에서 명시적으로 언급된 정보만 추출하세요.
2. 추측하지 마세요. 정보가 없으면 null로 표시하세요.
3. evidence_list와 attachments는 배열 형태로 반환하세요.
4. written_date가 없으면 "{today}"를 사용하세요.
5. 금액은 숫자와 단위를 포함해서 작성하세요 (예: "300,000원")
6. 반드시 유효한 JSON 형식으로만 응답하세요. 다른 텍스트는 포함하지 마세요.

## 출력 형식 (JSON)
{{
  "complainant_name": "추출된 값 또는 null",
  "complainant_contact": "추출된 값 또는 null",
  "suspect_name": "추출된 값 또는 null",
  "suspect_contact": "추출된 값 또는 null",
  "incident_datetime": "추출된 값 또는 null",
  "incident_place": "추출된 값 또는 null",
  "crime_facts": "추출된 값 또는 null",
  "damage_amount": "추출된 값 또는 null",
  "complaint_reason": "추출된 값 또는 null",
  "evidence_list": ["항목1", "항목2"] 또는 null,
  "attachments": ["항목1"] 또는 null,
  "request_purpose": "추출된 값 또는 null",
  "written_date": "{today}"
}}
"""

    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(prompt)

    response_text = response.text.strip()

    # JSON 코드 블록 제거
    if response_text.startswith('```json'):
        response_text = response_text[7:]
    elif response_text.startswith('```'):
        response_text = response_text[3:]
    if response_text.endswith('```'):
        response_text = response_text[:-3]

    extracted_values = json.loads(response_text.strip())

    # null 값을 빈 문자열이나 빈 배열로 변환
    for key, value in extracted_values.items():
        if value is None:
            if key in ["evidence_list", "attachments"]:
                extracted_values[key] = []
            else:
                extracted_values[key] = ""

    return extracted_values


def create_document_from_situation(doc_type: str, situation_text: str, case_id: str = None) -> dict:
    """
    사용자의 상황 설명으로부터 문서를 자동 생성합니다.

    1. 템플릿 조회
    2. 상황 텍스트에서 값 추출
    3. 문서 생성

    Args:
        doc_type: 문서 유형
        situation_text: 사용자 상황 설명
        case_id: 연관 케이스 ID (선택)

    Returns:
        {
            "pass": bool,
            "content_md": str,
            "errors": list,
            "extracted_values": dict
        }
    """
    # 1. 템플릿 조회
    template = get_active_template(doc_type)
    if not template:
        return {
            "pass": False,
            "content_md": "",
            "errors": ["TEMPLATE_NOT_FOUND"],
            "extracted_values": {}
        }

    try:
        # 2. 상황 텍스트에서 값 추출
        extracted_values = extract_values_from_situation(situation_text, template)

        # 3. 기존 문서 생성 로직 사용
        result = create_document(doc_type, extracted_values, case_id)

        # 추출된 값도 함께 반환
        result["extracted_values"] = extracted_values

        return result

    except json.JSONDecodeError as e:
        return {
            "pass": False,
            "content_md": "",
            "errors": [f"EXTRACTION_ERROR: JSON 파싱 실패 - {str(e)}"],
            "extracted_values": {}
        }
    except ValueError as e:
        return {
            "pass": False,
            "content_md": "",
            "errors": [f"CONFIG_ERROR: {str(e)}"],
            "extracted_values": {}
        }
    except Exception as e:
        return {
            "pass": False,
            "content_md": "",
            "errors": [f"EXTRACTION_ERROR: {str(e)}"],
            "extracted_values": {}
        }


def create_document(doc_type: str, values: dict, case_id: str = None) -> dict:
    """
    문서 생성 전체 프로세스를 수행합니다.

    1. 템플릿 조회
    2. Gemini로 문서 생성
    3. 검증
    4. DB 저장

    Args:
        doc_type: 문서 유형
        values: 변수 값 딕셔너리
        case_id: 연관 케이스 ID (선택)

    Returns:
        {
            "pass": bool,
            "content_md": str,
            "errors": list
        }
    """
    # 1. 템플릿 조회
    template = get_active_template(doc_type)
    if not template:
        return {
            "pass": False,
            "content_md": "",
            "errors": ["TEMPLATE_NOT_FOUND"]
        }

    try:
        # 2. Gemini로 문서 생성
        generated_content = generate_document_with_gemini(template, values)

        # 3. 검증
        validation_result = validate_document(
            template_content=template.content_md,
            generated_content=generated_content
        )

        # 4. DB 저장
        Document.objects.create(
            template=template,
            case_id=case_id,
            content_md=generated_content,
            validation_result=validation_result,
            input_values=values
        )

        return {
            "pass": validation_result["pass"],
            "content_md": generated_content,
            "errors": validation_result["errors"]
        }

    except ValueError as e:
        return {
            "pass": False,
            "content_md": "",
            "errors": [f"CONFIG_ERROR: {str(e)}"]
        }
    except Exception as e:
        return {
            "pass": False,
            "content_md": "",
            "errors": [f"GENERATION_ERROR: {str(e)}"]
        }
