from rest_framework import serializers
from .models import Message

class AIChatResponseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk')
    order = serializers.IntegerField(source='chat_order')

    class Meta:
        model = Message
        fields = ['id', 'order', 'role', 'content']



class CreateSessionSerializer(serializers.Serializer):
    message = serializers.CharField(required=True, help_text="첫 메시지 내용")
