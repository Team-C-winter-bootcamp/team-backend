# Fix INDEX_NAME reference in cases/service.py
with open('cases/service.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace INDEX_NAME with CHUNKED_INDEX_NAME
content = content.replace(
    "raise NotFoundError(f\"인덱스 '{INDEX_NAME}'를 찾을 수 없습니다.\")",
    "raise NotFoundError(f\"인덱스 '{CHUNKED_INDEX_NAME}'를 찾을 수 없습니다.\")"
)

# Fix summarize_precedent method
old_summarize = """        prompt = f\"\"\"다음 판례 전문을 읽고 핵심 내용을 요약해주세요. 
법률적 쟁점, 판결 요지, 주요 판단 근거를 중심으로 간결하게 정리해주세요.

판례 전문:
{precedent_content}

요약:\"\"\"
        
        return cls.generate_answer(prompt, temperature=0.3, max_output_tokens=1024)"""

new_summarize = """        prompt = \"\"\"다음 판례 전문을 읽고 핵심 내용을 요약해주세요. 
법률적 쟁점, 판결 요지, 주요 판단 근거를 중심으로 간결하게 정리해주세요.\"\"\"
        
        return GeminiService.generate_answer(prompt, context=precedent_content, temperature=0.3, max_output_tokens=1024)"""

content = content.replace(old_summarize, new_summarize)

with open('cases/service.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed INDEX_NAME references")
