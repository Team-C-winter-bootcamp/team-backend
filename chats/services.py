import os
import requests
from django.db import transaction
from .models import Message

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")

class OllamaService:
    @staticmethod
    def ask_ai(content):
        url = f"{OLLAMA_URL}/api/chat"
        payload = {
            "model": "llama3.2",
            "messages": [{"role": "user", "content": content}],
            "stream": False
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get('message', {}).get('content', "답변 생성 실패")
        except Exception as e:
            return f"Ollama 연결 에러: {str(e)}"

class ChatService:
    def generate_session_title(first_message):
        """
        사용자의 첫 메시지를 바탕으로 Ollama에게 짧은 제목 생성을 요청합니다.
        """
        prompt = (
            f"다음 메시지의 주제를 10자 이내의 한국어 제목으로 요약해줘: '{first_message}'\n"
            "설명 없이 딱 제목만 말해."
        )

        generated_title = OllamaService.ask_ai(prompt)

        if "Ollama 연결 에러" in generated_title or generated_title == "답변 생성 실패":
            return "새로운 채팅"

        # 앞뒤 백슬래시, 따옴표, 공백 제거
        generated_title = generated_title.strip()
        # 백슬래시 제거
        generated_title = generated_title.replace('\\', '')
        # 따옴표 제거 (단일 및 이중 따옴표)
        generated_title = generated_title.strip('"').strip("'").strip('"').strip("'")
        # 최종 공백 제거
        generated_title = generated_title.strip()
        
        return generated_title

    @staticmethod
    @transaction.atomic  # 유저/AI 메시지 저장은 한 번에 성공해야 하므로 원자성 보장
    def create_chat_pair(session, user_content):
        """새로운 채팅 쌍 생성 (POST)"""
        # 1. 유저 메시지 저장
        last_order = session.messages.count()
        Message.objects.create(
            session=session,
            role='user',
            content=user_content,
            chat_order=last_order + 1
        )

        # 2. AI 답변 생성 및 저장
        ai_content = OllamaService.ask_ai(user_content)
        ai_message = Message.objects.create(
            session=session,
            role='assistant',
            content=ai_content,
            chat_order=last_order + 2
        )
        return ai_message

    @staticmethod
    @transaction.atomic
    def update_chat_by_replacement(session, original_user_msg, new_content):
        """
        기존 메시지 쌍을 is_deleted 처리하고, 새로운 메시지 쌍을 생성함.
        """
        # 1. 기존 유저 메시지 soft delete
        original_user_msg.is_deleted = True
        original_user_msg.save()

        # 2. 기존 AI 메시지 찾아서 soft delete (유저 메시지 바로 다음 순서)
        original_ai_msg = Message.objects.filter(
            session=session,
            chat_order=original_user_msg.chat_order + 1,
            role='assistant',
            is_deleted=False
        ).first()

        if original_ai_msg:
            original_ai_msg.is_deleted = True
            original_ai_msg.save()

        # 3. 새로운 유저 메시지 생성 (기존과 동일한 chat_order 부여)
        new_user_msg = Message.objects.create(
            session=session,
            role='user',
            content=new_content,
            chat_order=original_user_msg.chat_order  # 위치 유지를 위해 같은 순서 사용
        )

        # 4. 새로운 AI 답변 생성
        new_ai_content = OllamaService.ask_ai(new_content)

        # 5. 새로운 AI 메시지 생성
        new_ai_msg = Message.objects.create(
            session=session,
            role='assistant',
            content=new_ai_content,
            chat_order=original_user_msg.chat_order + 1
        )

        return new_ai_msg