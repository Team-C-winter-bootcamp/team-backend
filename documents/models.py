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
