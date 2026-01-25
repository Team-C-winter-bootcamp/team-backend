from django.contrib import admin
from .models import Category, Question, Case


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
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content

    content_preview.short_description = '질문 내용'


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """사건(판례 검색 이력) 관리"""
    list_display = ('id', 'category', 'who', 'when', 'what_preview', 'is_deleted', 'created_at')
    list_filter = ('category', 'is_deleted', 'created_at')
    search_fields = ('who', 'what', 'detail', 'category__name')
    raw_id_fields = ('category',)
    ordering = ('-created_at',)

    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('기본 정보', {
            'fields': ('category', 'is_deleted')
        }),
        ('상황 정보 (Case Details)', {
            'fields': ('who', 'when', 'what', 'want', 'detail'),
            'description': '사용자가 입력한 상세 상황 정보입니다.'
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at'),  # 이제 readonly_fields 덕분에 에러가 나지 않습니다.
            'classes': ('collapse',)
        }),
    )

    def what_preview(self, obj):
        """사건 내용 요약 미리보기"""
        return obj.what[:30] + '...' if obj.what and len(obj.what) > 30 else obj.what

    what_preview.short_description = '사건 내용 요약'

