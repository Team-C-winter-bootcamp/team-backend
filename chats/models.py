from django.db import models
from django.conf import settings

class Session(models.Model):
    # 2. 외래키 설정 수정
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # '.config.settings' 대신 이 상수를 사용합니다.
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    title = models.CharField(max_length=50, null=False)
    bookmark = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "sessions"
        verbose_name = "채팅 세션"
        verbose_name_plural = "채팅 세션 목록"

    def __str__(self):
        return f"[{self.user.email}] {self.title}"


class Message(models.Model):
    ROLE_CHOICES = (
        ("user", "user"),
        ("assistant", "assistant"),
        ("system", "system"),
    )

    session = models.ForeignKey(
        Session,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    chat_order = models.IntegerField(null=False)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "messages"
        ordering = ["chat_order"]
