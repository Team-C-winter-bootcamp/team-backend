from rest_framework import serializers


class DocumentGenerateRequestSerializer(serializers.Serializer):
    """문서 생성 요청 시리얼라이저"""
    doc_type = serializers.CharField(
        help_text="문서 유형 (예: criminal_complaint_fraud)"
    )
    values = serializers.DictField(
        child=serializers.JSONField(),
        help_text="템플릿 변수 값들"
    )
    case_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="연관 케이스 ID (선택)"
    )


class DocumentGenerateResponseSerializer(serializers.Serializer):
    """문서 생성 응답 시리얼라이저"""
    pass_validation = serializers.BooleanField(
        source='pass',
        help_text="검증 통과 여부"
    )
    content_md = serializers.CharField(
        help_text="생성된 Markdown 문서"
    )
    errors = serializers.ListField(
        child=serializers.CharField(),
        help_text="오류 목록"
    )


class DocumentGenerateFromSituationRequestSerializer(serializers.Serializer):
    """상황 기반 문서 생성 요청 시리얼라이저"""
    doc_type = serializers.CharField(
        help_text="문서 유형 (예: criminal_complaint_fraud)"
    )
    situation = serializers.CharField(
        help_text="사용자가 자유롭게 작성한 상황 설명"
    )
    case_id = serializers.CharField(
        required=False,
        allow_null=True,
        help_text="연관 케이스 ID (선택)"
    )


class DocumentGenerateFromSituationResponseSerializer(serializers.Serializer):
    """상황 기반 문서 생성 응답 시리얼라이저"""
    pass_validation = serializers.BooleanField(
        source='pass',
        help_text="검증 통과 여부"
    )
    content_md = serializers.CharField(
        help_text="생성된 Markdown 문서"
    )
    errors = serializers.ListField(
        child=serializers.CharField(),
        help_text="오류 목록"
    )
    extracted_values = serializers.DictField(
        help_text="상황 텍스트에서 추출된 값들"
    )
