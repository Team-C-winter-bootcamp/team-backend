# chats/admin.py
from django.contrib import admin
from .models import Session, Message

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'title', 'bookmark', 'is_deleted', 'created_at')
    list_filter = ('bookmark', 'is_deleted', 'created_at')
    search_fields = ('title', 'user__email', 'user__clerk_id')
    readonly_fields = ('created_at', 'updated_at')
    list_editable = ('bookmark',)
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('user', 'title', 'bookmark')
        }),
        ('상태 정보', {
            'fields': ('is_deleted',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'chat_order', 'content_preview', 'is_deleted', 'created_at')
    list_filter = ('role', 'is_deleted', 'created_at')
    search_fields = ('content', 'session__title', 'session__user__email')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('기본 정보', {
            'fields': ('session', 'role', 'chat_order', 'content')
        }),
        ('상태 정보', {
            'fields': ('is_deleted',)
        }),
        ('타임스탬프', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def content_preview(self, obj):
        """메시지 내용 미리보기"""
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '내용 미리보기'