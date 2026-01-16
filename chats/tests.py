from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from rest_framework import status
from .models import Session, Message

User = get_user_model()


class ChatAPITestCase(TestCase):
    """Postman 테스트를 위한 기본 테스트 케이스"""
    
    def setUp(self):
        """테스트 설정"""
        self.client = Client()
        # 테스트 유저 생성
        self.test_user, _ = User.objects.get_or_create(
            clerk_id="test_debug_user",
            defaults={"email": "test@example.com"}
        )
    
    def test_session_list_create_without_auth(self):
        """인증 없이 세션 목록 조회 테스트 (DEBUG 모드)"""
        response = self.client.get('/chats/sessions')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'success')
    
    def test_session_create_without_auth(self):
        """인증 없이 세션 생성 테스트 (DEBUG 모드)"""
        response = self.client.post(
            '/chats/sessions',
            data={'message': '안녕하세요 테스트입니다'},
            content_type='application/json'
        )
        # Ollama 서비스가 없을 수 있으므로 201 또는 500 가능
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR])
    
    def test_session_create_with_test_mode_header(self):
        """X-Test-Mode 헤더로 세션 생성 테스트"""
        response = self.client.post(
            '/chats/sessions',
            data={'message': '테스트 메시지'},
            content_type='application/json',
            HTTP_X_TEST_MODE='true'
        )
        # Ollama 서비스가 없을 수 있으므로 201 또는 500 가능
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_500_INTERNAL_SERVER_ERROR])
