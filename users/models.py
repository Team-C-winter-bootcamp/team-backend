from django.db import models


class User(models.Model):
    """
    Clerk 사용자 정보와 동기화되는 모델
    """
    user_id = models.AutoField(primary_key=True, help_text="PK")
    clerk_id = models.CharField(max_length=255, unique=True, help_text="Clerk User ID")
    email = models.EmailField(max_length=50, unique=True)
    # password 필드는 Clerk에서 인증을 처리하므로 주석 처리합니다.
    # password = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자 목록"
        ordering = ["-created_at"]