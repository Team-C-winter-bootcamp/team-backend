import re
from typing import Tuple


def extract_headers(markdown_content: str) -> set:
    """
    Markdown 콘텐츠에서 헤더(#, ##, ### 등)를 추출합니다.

    Args:
        markdown_content: Markdown 형식의 문자열

    Returns:
        헤더 텍스트의 집합 (# 기호 제외, 공백 정규화)
    """
    header_pattern = r'^(#{1,6})\s+(.+)$'
    headers = set()

    for line in markdown_content.split('\n'):
        match = re.match(header_pattern, line.strip())
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
            headers.add((level, title))

    return headers


def has_unresolved_placeholders(content: str) -> Tuple[bool, list]:
    """
    콘텐츠에 미해결 플레이스홀더({{...}})가 있는지 확인합니다.

    Args:
        content: 검사할 문자열

    Returns:
        (미해결 여부, 미해결 플레이스홀더 목록)
    """
    placeholder_pattern = r'\{\{([^}]+)\}\}'
    matches = re.findall(placeholder_pattern, content)
    return len(matches) > 0, matches


def validate_document(template_content: str, generated_content: str) -> dict:
    """
    생성된 문서가 템플릿 구조를 준수하는지 검증합니다.

    검증 규칙:
    1. {{...}} 형태의 placeholder가 하나라도 남아 있으면 FAIL
    2. 템플릿의 헤더 목록이 결과에 모두 존재해야 PASS
    3. 결과 헤더 집합이 템플릿 헤더 집합을 초과하면 FAIL

    Args:
        template_content: 원본 템플릿 Markdown
        generated_content: 생성된 문서 Markdown

    Returns:
        {
            "pass": bool,
            "errors": list[str]
        }
    """
    errors = []

    # 1. 미해결 플레이스홀더 검사
    has_unresolved, unresolved_list = has_unresolved_placeholders(generated_content)
    if has_unresolved:
        errors.append("UNRESOLVED_PLACEHOLDER")

    # 2. 템플릿과 생성 문서의 헤더 추출
    template_headers = extract_headers(template_content)
    generated_headers = extract_headers(generated_content)

    # 3. 템플릿에 있는 모든 헤더가 생성 문서에 존재하는지 확인
    missing_headers = template_headers - generated_headers
    if missing_headers:
        errors.append("MISSING_SECTION")

    # 4. 생성 문서에 템플릿에 없는 추가 헤더가 있는지 확인
    extra_headers = generated_headers - template_headers
    if extra_headers:
        errors.append("EXTRA_SECTION")

    return {
        "pass": len(errors) == 0,
        "errors": errors
    }
