import uuid
from django.db import models


class Template(models.Model):
    """문서 템플릿 모델"""
    doc_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="문서 유형 (예: criminal_complaint_fraud)"
    )
    name = models.CharField(
        max_length=200,
        help_text="템플릿 이름"
    )
    version = models.PositiveIntegerField(
        default=1,
        help_text="템플릿 버전"
    )
    content_md = models.TextField(
        help_text="Markdown 형식의 템플릿 내용 ({{variable_name}} 플레이스홀더 포함)"
    )
    variables = models.JSONField(
        default=list,
        help_text="템플릿에서 사용하는 변수 목록"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="활성화 여부"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_templates'
        verbose_name = '문서 템플릿'
        verbose_name_plural = '문서 템플릿들'
        unique_together = [['doc_type', 'version']]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} (v{self.version})"


class Document(models.Model):
    """생성된 문서 모델"""
    template = models.ForeignKey(
        Template,
        on_delete=models.PROTECT,
        related_name='documents',
        help_text="사용된 템플릿"
    )
    case_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="연관된 케이스 ID (선택)"
    )
    content_md = models.TextField(
        help_text="생성된 Markdown 문서 내용"
    )
    validation_result = models.JSONField(
        default=dict,
        help_text="검증 결과 (pass, errors)"
    )
    input_values = models.JSONField(
        default=dict,
        help_text="입력된 변수 값들"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'generated_documents'
        verbose_name = '생성된 문서'
        verbose_name_plural = '생성된 문서들'
        ordering = ['-created_at']

    def __str__(self):
        return f"Document #{self.id} ({self.template.name})"


class DocumentSession(models.Model):
    """문서 작성 세션 모델"""

    class Status(models.TextChoices):
        WAITING = 'waiting', '대기 중'
        EXTRACTING = 'extracting', '값 추출 중'
        QUESTIONING = 'questioning', '추가 질문 중'
        GENERATING = 'generating', '문서 생성 중'
        COMPLETED = 'completed', '완료'
        FAILED = 'failed', '실패'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    case_id = models.IntegerField(db_index=True, help_text="연관된 케이스 ID")
    document_type = models.CharField(max_length=100, help_text="문서 유형 (한글 또는 영문)")
    template = models.ForeignKey(
        Template,
        on_delete=models.PROTECT,
        related_name='sessions',
        help_text="사용할 템플릿"
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.WAITING,
        help_text="세션 상태"
    )
    values = models.JSONField(default=dict, help_text="수집된 변수 값들")
    required_keys = models.JSONField(default=list, help_text="필수 변수 키 목록")
    last_draft = models.TextField(blank=True, null=True, help_text="최근 생성된 문서 초안")
    document = models.ForeignKey(
        'Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sessions',
        help_text="최종 생성된 문서"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'document_sessions'
        verbose_name = '문서 작성 세션'
        verbose_name_plural = '문서 작성 세션들'
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.id} ({self.document_type}) - {self.status}"


class DocumentSessionMessage(models.Model):
    """세션 메시지 모델"""

    class Role(models.TextChoices):
        USER = 'user', '사용자'
        ASSISTANT = 'assistant', '어시스턴트'
        SYSTEM = 'system', '시스템'

    session = models.ForeignKey(
        DocumentSession,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="연관된 세션"
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        help_text="메시지 역할"
    )
    content = models.TextField(help_text="메시지 내용")
    extracted_values = models.JSONField(
        default=dict,
        blank=True,
        help_text="이 메시지에서 추출된 값들"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_session_messages'
        verbose_name = '세션 메시지'
        verbose_name_plural = '세션 메시지들'
        ordering = ['created_at']

    def __str__(self):
        return f"[{self.role}] {self.content[:50]}..."
