import requests

class OllamaService:
    @staticmethod
    def ask_ai(content):
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": content}],
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            return response.json().get('message', {}).get('content', "답변 생성 실패")
        except Exception as e:
            return f"Ollama 연결 에러: {str(e)}"