from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    """
    Django Admin에서 User 모델을 관리하기 위한 설정
    """
    list_display = ('id', 'clerk_id', 'email', 'is_staff', 'is_superuser', 'is_deleted', 'updated_at')
    list_filter = ('is_staff', 'is_superuser', 'is_deleted')
    search_fields = ('email', 'clerk_id')
    readonly_fields = ('id', 'clerk_id', 'email', 'created_at', 'updated_at')
    list_editable = ('is_staff', 'is_superuser')

    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'clerk_id', 'email')
        }),
        ('권한 정보', {
            'fields': ('is_staff', 'is_superuser')
        }),
        ('상태 정보', {
            'fields': ('is_deleted',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )