from rest_framework import serializers
from .models import Message

class AIChatResponseSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='pk')
    order = serializers.IntegerField(source='chat_order')

    class Meta:
        model = Message
        fields = ['id', 'order', 'role', 'content']