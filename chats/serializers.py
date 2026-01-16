from rest_framework import serializers
from .models import Message, Session

class AIChatResponseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk', help_text="메시지 ID")
    order = serializers.IntegerField(source='chat_order', help_text="메시지 순서")
    role = serializers.CharField(help_text="메시지 역할 (user/assistant/system)")
    content = serializers.CharField(help_text="메시지 내용")

    class Meta:
        model = Message
        fields = ['id', 'order', 'role', 'content']


class SessionCreateRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, help_text="첫 메시지 내용 (세션 제목 생성에 사용)")


class SessionUpdateRequestSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, help_text="세션 제목")
    bookmark = serializers.BooleanField(required=False, help_text="북마크 여부")


class ChatMessageRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, help_text="사용자 메시지 내용")


class ChatUpdateRequestSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, help_text="수정할 메시지 내용")