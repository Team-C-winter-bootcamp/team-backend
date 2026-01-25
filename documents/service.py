import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

def generate_legal_document(case_data: str, precedent_data: str, template_content: str) -> str:
    # 1. 환경 변수 기반 LLM 설정
    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash").replace("models/", "").strip()

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.1, # 법률 문서의 일관성을 위해 낮게 설정
        max_output_tokens=4096
    )

    # 2. 프롬프트 구성
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 대한민국의 법률 전문가이자 전문 변호사입니다. "
            "제공된 [기본 템플릿]의 구조와 서식을 엄격히 준수하여 문서를 작성하십시오.\n\n"

            "**출력 형식 규칙 (필독):**\n"
            "1. **서론, 인사말, 부연 설명, 작성 의견 등을 절대로 포함하지 마십시오.**\n"
            "2. '제공해주신 템플릿을 바탕으로...'와 같은 서술형 문장을 모두 제거하고, 오직 완성된 **[내용증명서] 또는 [고소장]의 본문만** 출력하십시오.\n"
            "3. 마크다운(Markdown) 형식을 사용하여 문서의 격식을 유지하십시오.\n\n"

            "**작성 및 보강 원칙:**\n"
            "1. [참고 판례]를 문서를 구성하는 최우선 법리적 근거로 삼으십시오.\n"
            "2. 당신이 알고 있는 최신 대법원 판례, 관련 법리, 법령 해석을 적극 추가하여 내용을 더욱 풍부하게 보강하십시오.\n\n"

            "**데이터 유지 규칙:**\n"
            "1. [사건 내용]에 명시되지 않은 인적 사항(성명, 주소 등)은 절대 지어내지 마십시오.\n"
            "2. 정보가 없는 항목은 템플릿의 원래 변수 형태를 그대로 남겨두십시오. (예: {{sender_name}}, {{receiver_address}})\n"
            "3. 중괄호 `{{ }}`를 포함한 변수명을 토씨 하나 틀리지 않게 유지하십시오."
        )),
        ("human", (
            "[기본 템플릿]:\n{template}\n\n"
            "[사건 내용]:\n{case}\n\n"
            "[참고 판례]:\n{precedent}"
        ))
    ])

    # 3. Chain 실행
    chain = prompt | llm | StrOutputParser()

    try:
        return chain.invoke({
            "template": template_content,
            "case": case_data,
            "precedent": precedent_data
        })
    except Exception as e:
        logging.error(f"AI Generation Error: {e}")
        raise RuntimeError(f"AI 문서 생성 중 오류가 발생했습니다: {str(e)}")


def edit_legal_document_with_ai(original_content: str, user_request: str) -> str:
    llm = ChatGoogleGenerativeAI(
        model=os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview"),
        google_api_key=os.environ.get("GEMINI_API_KEY"),
        temperature=0.1  # 법률 문서이므로 창의성보다는 정확도를 위해 낮게 설정
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "당신은 법률 전문 AI 어시스턴트입니다. 제공된 [원본 문서]의 틀을 유지하며 "
            "사용자의 [수정 요청] 사항만 정확히 반영하여 문서를 완성하십시오.\n\n"
            "**수정 가이드:**\n"
            "1. 기존의 {{변수}} 형태는 수정 요청에 언급된 경우에만 실제 데이터로 치환하십시오.\n"
            "2. 언급되지 않은 다른 변수나 법률적 논리는 그대로 유지하십시오.\n"
            "3. 인사말이나 부연 설명 없이 오직 '수정된 문서 본문'만 출력하십시오."
        )),
        ("human", "[원본 문서]:\n{original_content}\n\n[수정 요청]:\n{user_request}")
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"original_content": original_content, "user_request": user_request})