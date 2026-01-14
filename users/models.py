from django.db import models


class User(models.Model):
    """
    Clerk 사용자 정보와 동기화되는 모델
    """
    clerk_id = models.CharField(max_length=255, primary_key=True, help_text="Clerk User ID")
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=255, blank=True, null=True)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    image_url = models.URLField(max_length=2000, blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Soft delete flag")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자 목록"
        ordering = ["-created_at"]