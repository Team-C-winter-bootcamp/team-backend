from rest_framework import serializers
from .models import Case, Category

class CaseSerializer(serializers.Serializer):
    category = serializers.CharField(help_text="카테고리명 (예: 부동산)")
    who = serializers.CharField(help_text="당사자 정보 (예: 임차인)")
    when = serializers.CharField(help_text="사건 시기 (예: 2024년 1월)")
    what = serializers.CharField(help_text="사건 내용 (예: 보증금 미반환)")
    want = serializers.CharField(help_text="원하는 결과 (예: 보증금 반환)")
    detail = serializers.CharField(help_text="상세 설명")

class CaseResultSerializer(serializers.Serializer):
    status = serializers.CharField()
    code = serializers.IntegerField()
    message = serializers.CharField()
    data = serializers.JSONField()



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

# --- 사건 심층 분석을 위한 Serializers 추가 ---

class OutcomePredictionSerializer(serializers.Serializer):
    """결과 예측 정보"""
    win_probability = serializers.FloatField(help_text="승소 확률 (0.0 ~ 1.0 또는 0 ~ 100)")
    expected_compensation = serializers.CharField(help_text="예상 보상액 (예: '500만원 ~ 1000만원')", allow_blank=True)
    estimated_duration = serializers.CharField(help_text="예상 소요 기간 (예: '3개월 ~ 6개월')", allow_blank=True)
    risk_factors = serializers.ListField(
        child=serializers.CharField(),
        help_text="위험 요소 리스트",
        allow_empty=True
    )
    confidence_level = serializers.CharField(help_text="예측 신뢰도 (예: '높음', '보통', '낮음')", allow_blank=True)

class ActionStepSerializer(serializers.Serializer):
    """행동 지침의 개별 단계"""
    step_number = serializers.IntegerField(help_text="단계 번호")
    title = serializers.CharField(help_text="단계 제목")
    description = serializers.CharField(help_text="단계 설명")
    priority = serializers.CharField(help_text="우선순위 (예: '필수', '권장')", allow_blank=True)
    estimated_time = serializers.CharField(help_text="예상 소요 시간", allow_blank=True)

class ActionRoadmapSerializer(serializers.Serializer):
    """행동 지침 (액션 플랜)"""
    steps = ActionStepSerializer(many=True, help_text="단계별 액션 플랜")
    summary = serializers.CharField(help_text="전체 로드맵 요약", allow_blank=True)

class EvidenceItemSerializer(serializers.Serializer):
    """증거 항목"""
    name = serializers.CharField(help_text="증거명")
    type = serializers.CharField(help_text="증거 유형 (REQUIRED 또는 RECOMMENDED)")
    description = serializers.CharField(help_text="증거 설명", allow_blank=True)
    collection_tips = serializers.CharField(help_text="수집 팁", allow_blank=True)

class EvidenceStrategySerializer(serializers.Serializer):
    """증거 전략"""
    required_evidence = EvidenceItemSerializer(many=True, help_text="필수 증거 목록")
    recommended_evidence = EvidenceItemSerializer(many=True, help_text="권장 증거 목록")
    general_tips = serializers.CharField(help_text="일반적인 증거 수집 가이드", allow_blank=True)

class PrecedentInfoSerializer(serializers.Serializer):
    """유사 판례 정보"""
    case_number = serializers.CharField(help_text="사건번호")
    case_title = serializers.CharField(help_text="사건명")
    relevance = serializers.CharField(help_text="관련성 설명", allow_blank=True, required=False, default="")
    key_points = serializers.ListField(
        child=serializers.CharField(),
        help_text="핵심 포인트 리스트",
        allow_empty=True,
        required=False,
        default=list
    )

class LegalFoundationSerializer(serializers.Serializer):
    """법적 근거"""
    applicable_laws = serializers.ListField(
        child=serializers.CharField(),
        help_text="적용 법률 조항 리스트 (예: ['민법 제570조', '민법 제571조'])",
        allow_empty=True
    )
    legal_principles = serializers.ListField(
        child=serializers.CharField(),
        help_text="법적 원칙 설명 리스트",
        allow_empty=True
    )
    relevant_precedents = PrecedentInfoSerializer(many=True, help_text="유사 판례 정보", allow_empty=True)

class CaseAnalysisDataSerializer(serializers.Serializer):
    """사건 심층 분석 데이터"""
    outcome_prediction = OutcomePredictionSerializer(help_text="결과 예측")
    action_roadmap = ActionRoadmapSerializer(help_text="행동 지침")
    evidence_strategy = EvidenceStrategySerializer(help_text="증거 전략")
    legal_foundation = LegalFoundationSerializer(help_text="법적 근거")

class CaseAnalysisResponseSerializer(serializers.Serializer):
    """사건 심층 분석 응답 구조"""
    status = serializers.CharField(help_text="응답 상태")
    code = serializers.IntegerField(help_text="HTTP 상태 코드")
    message = serializers.CharField(help_text="응답 메시지")
    data = CaseAnalysisDataSerializer(help_text="심층 분석 데이터")