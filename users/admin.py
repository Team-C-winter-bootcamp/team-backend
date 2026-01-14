from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Django Admin에서 User 모델을 관리하기 위한 설정
    """
    list_display = ('user_id', 'clerk_id', 'email', 'is_deleted', 'updated_at')
    list_filter = ('is_deleted',)
    search_fields = ('email', 'clerk_id')
    readonly_fields = ('user_id', 'clerk_id', 'email', 'created_at', 'updated_at')

    fieldsets = (
        ('기본 정보', {
            'fields': ('user_id', 'clerk_id', 'email')
        }),
        ('상태 정보', {
            'fields': ('is_deleted',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )