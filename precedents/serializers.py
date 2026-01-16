from rest_framework import serializers
from .models import Precedent

class PrecedentListSerializer(serializers.ModelSerializer):
    precedents_id = serializers.IntegerField(source='id')
    case_preview = serializers.SerializerMethodField()
    outcome_display = serializers.SerializerMethodField()

    class Meta:
        model = Precedent
        # 목록: ID, 제목, 미리보기, 결과
        fields = ['precedents_id', 'case_title', 'case_preview', 'outcome_display']

    def get_case_preview(self, obj):
        # 판결내용(judgment_content)의 앞 100자를 미리보기로 사용
        return obj.judgment_content[:100] if obj.judgment_content else ""

    def get_outcome_display(self, obj):
        # RelationOutcome 테이블을 조회하여 실제 결과 반환
        relation_outcomes = obj.relationoutcome_set.filter(is_deleted=False)
        if relation_outcomes.exists():
            # 첫 번째 결과의 outcome_type 반환 (여러 개가 있을 경우 첫 번째 것만)
            return relation_outcomes.first().outcome.outcome_type
        return "결과 없음"

class PrecedentDetailSerializer(serializers.ModelSerializer):
    # '원문' 데이터를 judgment_content 필드에서 가져와 full_text로 명명
    full_text = serializers.CharField(source='judgment_content')

    class Meta:
        model = Precedent
        # 상세: 사건 제목, 사건 이름, 판결내용(원문), 판결요지, 판시사항, 질문, 답변, 요약원문, 요약
        fields = [
            'case_title', 
            'case_name', 
            'full_text',
            'judgment_content',            'judgment_summary',
            'holdings',
            'question',
            'answer',
            'summary_original',
            'summary'
        ]