import os
import logging
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


def get_llm():
    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = os.environ.get("GEMINI_MODEL").replace("models/", "").strip()
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0.1,
        max_output_tokens=4096
    )


def generate_legal_document(case_data: str, precedent_data: str, template_content: str, doc_type_name: str) -> str:
    llm = get_llm()

    # 문서 타입별 특화 지침
    type_specific_instruction = {
        "complaint": "피고소인의 위법 행위를 육하원칙에 따라 명확히 기술하고, 관련 법령 위반 사실을 엄격하게 적시하십시오.",
        "notice": "발신인의 권리 주장과 수신인의 의무 이행 독촉 내용을 포함하며, 불이행 시 법적 조치 예고를 단호하게 작성하십시오.",
        "agreement": "갑과 을 사이의 상호 합의 사항을 명확히 하고, 향후 민형사상 이의 제기 금지(부제소 합의) 조항을 반드시 포함하십시오."
    }.get(doc_type_name, "")

    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            f"당신은 대한민국의 법률 전문가 변호사입니다. 지금부터 [내용증명서]를 작성합니다.\n"
            f"특이 지침: {type_specific_instruction}\n\n"
            "**작성 원칙:**\n"
            "1. 제공된 [기본 템플릿]의 변수(`{{ }}`)와 구조를 유지하십시오.\n"
            "2. [참고 판례]의 법리적 논거를 본문에 자연스럽게 녹여내어 전문성을 높이십시오.\n"
            "3. 인사말이나 서론 없이 바로 문서 본문만 마크다운 형식으로 출력하십시오."
        )),
        ("human", "[기본 템플릿]:\n{template}\n\n[사건 내용]:\n{case}\n\n[참고 판례]:\n{precedent}")
    ])

    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"template": template_content, "case": case_data, "precedent": precedent_data})


def edit_legal_document_with_ai(original_content: str, user_request: str) -> str:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "법률 전문 AI 어시스턴트입니다. 원본 문서의 틀을 유지하며 사용자의 수정 요청사항만 정확히 반영하십시오. 부연 설명 없이 본문만 출력합니다."),
        ("human", "[원본 문서]:\n{original_content}\n\n[수정 요청]:\n{user_request}")
    ])
    return (prompt | llm | StrOutputParser()).invoke(
        {"original_content": original_content, "user_request": user_request})