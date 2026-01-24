from django.contrib import admin
from .models import Template, Document, DocumentSession, DocumentSessionMessage


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'doc_type', 'version', 'is_active', 'created_at', 'updated_at']
    list_filter = ['doc_type', 'is_active', 'version']
    search_fields = ['name', 'doc_type']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'template', 'case_id', 'get_validation_status', 'created_at']
    list_filter = ['template__doc_type', 'created_at']
    search_fields = ['case_id', 'content_md']
    readonly_fields = ['template', 'content_md', 'validation_result', 'input_values', 'created_at']
    ordering = ['-created_at']

    def get_validation_status(self, obj):
        if obj.validation_result.get('pass', False):
            return '✓ PASS'
        return '✗ FAIL'
    get_validation_status.short_description = '검증 결과'


class DocumentSessionMessageInline(admin.TabularInline):
    model = DocumentSessionMessage
    extra = 0
    readonly_fields = ['role', 'content', 'extracted_values', 'created_at']
    can_delete = False


@admin.register(DocumentSession)
class DocumentSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'case_id', 'document_type', 'status', 'get_collected_count', 'created_at', 'updated_at']
    list_filter = ['status', 'document_type', 'created_at']
    search_fields = ['id', 'case_id', 'document_type']
    readonly_fields = ['id', 'template', 'values', 'required_keys', 'last_draft', 'document', 'created_at', 'updated_at']
    ordering = ['-created_at']
    inlines = [DocumentSessionMessageInline]

    def get_collected_count(self, obj):
        collected = len([k for k in obj.required_keys if k in obj.values and obj.values[k]])
        total = len(obj.required_keys)
        return f"{collected}/{total}"
    get_collected_count.short_description = '수집 진행'


@admin.register(DocumentSessionMessage)
class DocumentSessionMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'role', 'get_content_preview', 'created_at']
    list_filter = ['role', 'created_at']
    search_fields = ['content', 'session__id']
    readonly_fields = ['session', 'role', 'content', 'extracted_values', 'created_at']
    ordering = ['-created_at']

    def get_content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    get_content_preview.short_description = '내용 미리보기'
