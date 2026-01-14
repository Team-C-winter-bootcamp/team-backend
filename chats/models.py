from django.db import models


class Session(models.Model):
  #  clerk_user_id = models.CharField(max_length=50,null=False) 테스트용
    clerk_user_id = models.IntegerField(null=False)
    title = models.CharField(max_length=50, null=False)
    bookmark = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        db_table = "sessions"


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
