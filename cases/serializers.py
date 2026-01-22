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

class CaseSearchRequestSerializer(serializers.Serializer):
    """
    /api/cases/ POST 요청의 본문(body) 구조를 정의하는 Serializer.
    """
    category = serializers.CharField(help_text="사건 카테고리 (예: 부동산)")
    situation = SituationSerializer()

# --- 응답 Serializer ---

class CaseResultSerializer(serializers.Serializer):
    """유사 판례 검색 결과 리스트의 개별 항목"""
    id = serializers.IntegerField(help_text="판례 일련번호")
    case_number = serializers.CharField(help_text="사건 번호")
    case_title = serializers.CharField(help_text="사건명")
    law_category = serializers.CharField(help_text="법률 카테고리 (예: 민사)")
    law_subcategory = serializers.CharField(help_text="법률 하위 카테고리 (예: 전세금반환)")
    court = serializers.CharField(help_text="법원명")
    judgment_date = serializers.DateField(help_text="판결 일자")
    similarity_score = serializers.FloatField(help_text="유사도 점수")
    preview = serializers.CharField(help_text="판례 요약 (summ_contxt)")

class CaseSearchDataSerializer(serializers.Serializer):
    """응답의 'data' 필드"""
    total_count = serializers.IntegerField(help_text="검색된 총 판례 개수")
    results = CaseResultSerializer(many=True, help_text="유사 판례 검색 결과 리스트")

class CaseSearchResponseSerializer(serializers.Serializer):
    """/api/cases/ POST 최종 응답 형태"""
    status = serializers.CharField(help_text="응답 상태 (예: success)")
    code = serializers.IntegerField(help_text="HTTP 상태 코드")
    message = serializers.CharField(help_text="응답 메시지")
    data = CaseSearchDataSerializer(help_text="실제 응답 데이터")
