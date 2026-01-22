from django.contrib import admin
from .models import Category, Question, Case, Template


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """카테고리 관리"""
    list_display = ('category_id', 'name', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('is_deleted', 'created_at')
    search_fields = ('name',)
    list_editable = ('is_deleted',)
    ordering = ('-created_at',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """질문 관리"""
    list_display = ('question_id', 'category', 'content_preview', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('category', 'is_deleted', 'created_at')
    search_fields = ('content', 'category__name')
    raw_id_fields = ('category',)
    ordering = ('-created_at',)
    
    def content_preview(self, obj):
        """질문 내용 미리보기"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '질문 내용'


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """사건 관리"""
    list_display = ('id', 'category', 'user_info_preview', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('category', 'is_deleted', 'created_at')
    search_fields = ('category__name',)
    raw_id_fields = ('category',)
    readonly_fields = ('user_info_formatted',)
    ordering = ('-created_at',)
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'is_deleted')
        }),
        ('사용자 상황 정보', {
            'fields': ('user_info', 'user_info_formatted'),
            'description': 'JSON 형식의 사용자 상황 정보입니다.'
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def user_info_preview(self, obj):
        """사용자 정보 미리보기"""
        import json
        try:
            info_str = json.dumps(obj.user_info, ensure_ascii=False, indent=2)
            return info_str[:100] + '...' if len(info_str) > 100 else info_str
        except:
            return str(obj.user_info)[:100]
    user_info_preview.short_description = '사용자 정보'
    
    def user_info_formatted(self, obj):
        """포맷된 사용자 정보 (읽기 전용)"""
        import json
        try:
            return json.dumps(obj.user_info, ensure_ascii=False, indent=2)
        except:
            return str(obj.user_info)
    user_info_formatted.short_description = '포맷된 사용자 정보'


@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    """템플릿 관리"""
    list_display = ('template_id', 'type', 'is_deleted', 'created_at', 'updated_at')
    list_filter = ('type', 'is_deleted', 'created_at')
    search_fields = ('type',)
    list_editable = ('is_deleted',)
    ordering = ('-created_at',)
