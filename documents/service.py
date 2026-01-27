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

    # 1. 문서 타입별 명칭 및 특화 지침 매핑
    doc_meta = {
        "complaint": {
            "title": "고소장",
            "instruction": "피고소인의 위법 행위를 육하원칙에 따라 명확히 기술하고, 관련 법령 위반 사실을 엄격하게 적시하십시오."
        },
        "notice": {
            "title": "내용증명서",
            "instruction": "발신인의 권리 주장과 수신인의 의무 이행 독촉 내용을 포함하며, 불이행 시 법적 조치 예고를 단호하게 작성하십시오."
        },
        "agreement": {
            "title": "합의서",
            "instruction": "갑과 을 사이의 상호 합의 사항을 명확히 하고, 향후 민형사상 이의 제기 금지(부제소 합의) 조항을 반드시 포함하십시오."
        }
    }.get(doc_type_name, {"title": "법률 문서", "instruction": ""})

    # 2. 프롬프트 구성
    prompt = ChatPromptTemplate.from_messages([
        # prompt 구성 부분 수정
        ("system", (
            f"당신은 대한민국의 법률 전문가 변호사입니다. 지금부터 [{doc_meta['title']}]를 작성합니다.\n"
            f"특이 지침: {doc_meta['instruction']}\n\n"
            "**작성 원칙:**\n"
            "1. [기본 템플릿]의 구조를 완벽히 유지하며, 모든 변수(`{{ }}`)를 적절한 내용으로 치환하십시오.\n"
            "2. **증거 및 첨부자료 원칙:** `{{evidence_list}}`와 `{{attachments}}`는 반드시 [사건 내용]에 명시적으로 언급된 것만 기재하십시오.\n"
            "   - 만약 [사건 내용]에서 증거 정보를 찾을 수 없다면, 임의로 지어내지 말고 `해당 사항 없음` 또는 `[추후 제출]`이라고만 기재하십시오.\n"
            "3. **법리 적용:** [유사 판례]의 논거를 본문에 녹여내되, 판례에 나온 구체적 수치나 날짜를 [사건 내용]의 사실관계와 혼동하지 않도록 주의하십시오.\n"
            "4. 특정되지 않은 인적사항이나 날짜 등은 `[미정]`으로 남겨두십시오.\n"
            "5. 인사말 없이 문서 본문만 마크다운으로 출력하십시오."
        )),
        ("human", (
            "### [기본 템플릿]\n{template}\n\n"
            "### [사건 내용 (사용자 상황)]\n{case}\n\n"
            "### [유사 판례 및 법적 근거]\n{precedent}"
        ))
    ])

    chain = prompt | llm | StrOutputParser()

    return chain.invoke({
        "template": template_content,
        "case": case_data,
        "precedent": precedent_data
    })


def edit_legal_document_with_ai(original_content: str, user_request: str) -> str:
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "법률 전문 AI 어시스턴트입니다. 원본 문서의 틀을 유지하며 사용자의 수정 요청사항만 정확히 반영하십시오. 부연 설명 없이 본문만 출력합니다."),
        ("human", "[원본 문서]:\n{original_content}\n\n[수정 요청]:\n{user_request}")
    ])
    return (prompt | llm | StrOutputParser()).invoke(
        {"original_content": original_content, "user_request": user_request})