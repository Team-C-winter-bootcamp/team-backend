from rest_framework import serializers
from .models import Document

class DocumentCreateRequestSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="문서 종류")
    case_id = serializers.IntegerField(help_text="조회할 사건(Case)의 ID") # 수정됨
    precedent = serializers.CharField(help_text="참고할 판례 내용")

class DocumentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ['document_id', 'type', 'content']

class DocumentPatchRequestSerializer(serializers.Serializer):
    document_id = serializers.IntegerField(
        required=True,
        help_text="수정할 문서의 ID (DB 조회용)"
    )
    user_request = serializers.CharField(
        required=True,
        help_text="AI에게 내리는 수정 명령 (예: '이름을 박준제로 채워줘')"
    )