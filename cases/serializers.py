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

# --- 답변 생성(AI 분석)을 위한 Serializers 추가 ---

class CaseAnswerRequestSerializer(serializers.Serializer):
    """AI에게 특정 판례에 대한 질문을 던질 때 사용"""
    case_id = serializers.IntegerField(help_text="분석할 판례의 일련번호")
    query = serializers.CharField(help_text="사용자의 질문 또는 추가 상황 설명")

class CaseAnswerResponseSerializer(serializers.Serializer):
    """AI 분석 결과 응답 구조"""
    status = serializers.CharField()
    code = serializers.IntegerField()
    message = serializers.CharField()
    data = serializers.DictField(help_text="AI 분석 텍스트가 담길 곳")

# --- 판례 상세 조회를 위한 Serializers 추가 ---

class PrecedentDetailDataSerializer(serializers.Serializer):
    """판례 상세 정보"""
    case_number = serializers.CharField(help_text="사건번호")
    case_title = serializers.CharField(help_text="사건명")
    case_name = serializers.CharField(help_text="사건명 (caseNm)")
    court = serializers.CharField(help_text="법원명")
    judgment_date = serializers.DateField(help_text="판결일자")
    precedent_id = serializers.IntegerField(help_text="판례일련번호")
    issue = serializers.CharField(help_text="판시사항")
    holding = serializers.CharField(help_text="판결요지")
    content = serializers.CharField(help_text="판례내용 (전문)")
    summary = serializers.CharField(help_text="AI 요약")

class PrecedentDetailResponseSerializer(serializers.Serializer):
    """판례 상세 조회 응답 구조"""
    status = serializers.CharField(help_text="응답 상태")
    code = serializers.IntegerField(help_text="HTTP 상태 코드")
    message = serializers.CharField(help_text="응답 메시지")
    data = PrecedentDetailDataSerializer(help_text="판례 상세 정보")