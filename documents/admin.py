from django.contrib import admin
from .models import Template, Document


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
