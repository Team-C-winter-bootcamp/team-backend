# document/admin.py

from django.contrib import admin
from .models import Template, Document

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    # Template 모델은 template_id가 PK이므로 그대로 둡니다.
    list_display = ('template_id', 'type', 'created_at', 'updated_at', 'is_deleted')
    list_display_links = ('template_id', 'type')
    list_filter = ('type', 'is_deleted')
    search_fields = ('content', 'type')
    ordering = ('-created_at',)

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    # Document 모델은 document_id가 PK이므로 이름을 수정합니다.
    list_display = ('document_id', 'type', 'created_at', 'is_deleted')  # template_id -> document_id
    list_display_links = ('document_id', 'type')                       # template_id -> document_id
    list_filter = ('type', 'is_deleted')
    search_fields = ('content',)
    ordering = ('-created_at',)