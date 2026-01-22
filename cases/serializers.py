from rest_framework import serializers

class SituationSerializer(serializers.Serializer):
    """
    'situation' 객체의 구조를 정의하는 Serializer.
    """
    q1 = serializers.CharField(help_text="상황 질문 1에 대한 답변")
    q2 = serializers.CharField(help_text="상황 질문 2에 대한 답변")
    q3 = serializers.CharField(help_text="상황 질문 3에 대한 답변")
    q4 = serializers.CharField(help_text="상황 질문 4에 대한 답변")
    detail = serializers.CharField(help_text="상세 내용")

class RAGSearchRequestSerializer(serializers.Serializer):
    """
    /api/cases/rag-search/ POST 요청의 본문(body) 구조를 정의하는 Serializer.
    """
    category = serializers.CharField(help_text="사건 카테고리 (예: 부동산)")
    situation = SituationSerializer()
