from rest_framework import serializers

class DocumentCreateRequestSerializer(serializers.Serializer):
    case_id = serializers.IntegerField(help_text="사건 ID")
    precedent = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="참고할 판례 내용 (선택 사항)"
    )

class DocumentPatchRequestSerializer(serializers.Serializer):
    document_id = serializers.IntegerField(help_text="수정할 문서 ID")
    user_request = serializers.CharField(help_text="AI에게 전달할 수정 요청 사항")

class DocumentResponseSerializer(serializers.ModelSerializer):
    class Meta:
        from .models import Document
        model = Document
        fields = ['document_id', 'type', 'content',]