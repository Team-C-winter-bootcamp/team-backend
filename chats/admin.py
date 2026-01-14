# chats/admin.py
from django.contrib import admin
from .models import Session, Message

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_id', 'title', 'created_at') # 목록에 보여줄 항목

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'session', 'role', 'chat_order', 'created_at')
