from rest_framework import serializers
from .models import Category, Question


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        # 프론트에서 버튼을 만들 때 필요한 타입과 내용만 전달
        fields = ['type', 'content']

class InitDataSerializer(serializers.ModelSerializer):
    # 역참조를 통해 질문 리스트를 가져옴 (related_name='questions' 사용)
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['category_id', 'name', 'questions']

class CaseSerializer(serializers.Serializer):
    category = serializers.CharField(required=False, allow_blank=True, default='일반')
    who = serializers.CharField()
    when = serializers.CharField()
    what = serializers.CharField()
    want = serializers.CharField()
    detail = serializers.CharField()


class PrecedentResultSerializer(serializers.Serializer):
    case_No = serializers.CharField()
    case_name = serializers.CharField()
    case_title = serializers.CharField()
    law_category = serializers.CharField()
    law_subcategory = serializers.CharField()
    court = serializers.CharField()
    judgment_date = serializers.CharField()
    similarity = serializers.FloatField()
    preview = serializers.CharField(required=False, allow_blank=True)


class CaseSearchResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    code = serializers.IntegerField()
    message = serializers.CharField()
    data = serializers.DictField()


class PrecedentDetailResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    data = serializers.DictField()


class CaseAnswerApiResponseSerializer(serializers.Serializer):
    status = serializers.CharField(default="success")
    data = serializers.JSONField()