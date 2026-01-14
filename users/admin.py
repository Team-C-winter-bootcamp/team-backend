from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Django Admin에서 User 모델을 관리하기 위한 설정
    """
    # 목록 페이지에 표시할 필드들
    list_display = ('email', 'first_name', 'last_name', 'is_active', 'updated_at')
    
    # 필터링 옵션을 제공할 필드들
    list_filter = ('is_active',)
    
    # 검색 기능을 제공할 필드들
    search_fields = ('email', 'clerk_id', 'first_name', 'last_name')

    # 상세 페이지에서 읽기 전용으로 표시할 필드들
    # 이 필드들은 Clerk에서 동기화되므로 Admin에서 직접 수정하지 않도록 설정합니다.
    readonly_fields = (
        'clerk_id', 
        'email', 
        'first_name', 
        'last_name', 
        'image_url', 
        'created_at', 
        'updated_at'
    )

    # is_active 필드는 Admin에서 직접 수정 가능하도록 남겨둡니다.
    fieldsets = (
        ('기본 정보 (Clerk 동기화)', {
            'fields': ('clerk_id', 'email', 'first_name', 'last_name', 'image_url')
        }),
        ('상태 정보', {
            'fields': ('is_active',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )