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


# ============================================================
# 신규 API 명세용 시리얼라이저 (POST /cases/{case_id}/documents)
# ============================================================

class CaseDocumentCreateRequestSerializer(serializers.Serializer):
    """
    케이스 기반 문서 생성 요청 시리얼라이저
    POST /cases/{case_id}/documents
    """
    document_type = serializers.CharField(
        required=True,
        help_text="문서 유형 (예: 내용증명, criminal_complaint_fraud)"
    )
    case_id = serializers.IntegerField(
        required=True,
        help_text="케이스 ID (path parameter와 일치해야 함)"
    )
    values = serializers.DictField(
        required=False,
        default=dict,
        help_text="템플릿 변수 값들 (예: creditor_name, debtor_name 등)"
    )


class CaseDocumentDataSerializer(serializers.Serializer):
    """문서 생성 성공 시 data 필드"""
    document_id = serializers.IntegerField(help_text="생성된 문서 ID")
    case_id = serializers.IntegerField(help_text="케이스 ID")
    title = serializers.CharField(help_text="문서 제목")
    content = serializers.CharField(help_text="생성된 문서 내용 (Markdown)")


class CaseDocumentSuccessResponseSerializer(serializers.Serializer):
    """
    문서 생성 성공 응답 시리얼라이저
    HTTP 200 OK
    """
    status = serializers.CharField(default="success", help_text="응답 상태")
    data = CaseDocumentDataSerializer(help_text="응답 데이터")


class CaseDocumentErrorSerializer(serializers.Serializer):
    """에러 상세 정보"""
    additional_request = serializers.CharField(
        allow_null=True,
        help_text="추가 요청 정보"
    )


class CaseDocumentErrorResponseSerializer(serializers.Serializer):
    """
    문서 생성 에러 응답 시리얼라이저
    HTTP 400/404/500
    """
    status = serializers.CharField(default="error", help_text="응답 상태")
    code = serializers.IntegerField(help_text="HTTP 상태 코드")
    message = serializers.CharField(help_text="에러 메시지")
    error = CaseDocumentErrorSerializer(
        required=False,
        help_text="에러 상세 (400 에러 시에만 포함)"
    )


# ============================================================
# 세션 기반 문서 작성 API 시리얼라이저
# ============================================================

class DocumentSessionCreateRequestSerializer(serializers.Serializer):
    """
    세션 생성 요청 시리얼라이저
    POST /cases/{case_id}/document-sessions/
    """
    document_type = serializers.ChoiceField(
        choices=[
            ('내용증명서', '내용증명서'),
            ('내용증명', '내용증명'),
            ('고소장', '고소장'),
            ('합의서', '합의서'),
            ('proof_of_contents', 'proof_of_contents'),
            ('criminal_complaint_fraud', 'criminal_complaint_fraud'),
            ('settlement_agreement', 'settlement_agreement'),
        ],
        help_text="문서 유형 (내용증명서, 고소장, 합의서 등)"
    )


class DocumentSessionMessageRequestSerializer(serializers.Serializer):
    """
    세션 메시지 요청 시리얼라이저
    POST /cases/{case_id}/document-sessions/{session_id}/messages/
    """
    content = serializers.CharField(
        required=True,
        help_text="사용자 메시지 내용"
    )


class DocumentSessionMessageSerializer(serializers.Serializer):
    """세션 메시지 응답 시리얼라이저"""
    role = serializers.CharField(help_text="메시지 역할 (user, assistant, system)")
    content = serializers.CharField(help_text="메시지 내용")
    extracted_values = serializers.DictField(
        required=False,
        help_text="이 메시지에서 추출된 값들"
    )
    created_at = serializers.DateTimeField(help_text="생성 시간")


class DocumentSessionResponseSerializer(serializers.Serializer):
    """
    세션 상태 응답 시리얼라이저
    GET /cases/{case_id}/document-sessions/{session_id}/
    """
    session_id = serializers.UUIDField(help_text="세션 ID")
    case_id = serializers.IntegerField(help_text="케이스 ID")
    document_type = serializers.CharField(help_text="문서 유형")
    status = serializers.CharField(help_text="세션 상태")
    required_keys = serializers.ListField(
        child=serializers.CharField(),
        help_text="필수 키 목록"
    )
    collected_keys = serializers.ListField(
        child=serializers.CharField(),
        help_text="수집 완료된 키 목록"
    )
    missing_keys = serializers.ListField(
        child=serializers.CharField(),
        help_text="누락된 키 목록"
    )
    values = serializers.DictField(help_text="수집된 값들")
    messages = DocumentSessionMessageSerializer(many=True, help_text="메시지 목록")
    document_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="생성된 문서 ID (완료 시)"
    )
    created_at = serializers.DateTimeField(help_text="세션 생성 시간")
    updated_at = serializers.DateTimeField(help_text="세션 업데이트 시간")


class DocumentDetailSerializer(serializers.Serializer):
    """
    문서 상세 조회 응답 시리얼라이저
    GET /cases/{case_id}/documents/{document_id}/
    """
    document_id = serializers.IntegerField(help_text="문서 ID")
    case_id = serializers.IntegerField(help_text="케이스 ID")
    title = serializers.CharField(help_text="문서 제목 (템플릿명)")
    content = serializers.CharField(help_text="문서 내용 (Markdown)")
    validation_result = serializers.DictField(help_text="검증 결과")
    created_at = serializers.DateTimeField(help_text="생성 시간")
