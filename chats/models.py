from django.db import models

class ChatSession(models.Model):
    title = models.CharField(max_length=255) # 채팅방 제목
    bookmark = models.BooleanField(default=False) # 즐겨찾기

    # 임시: Clerk 유저 식별자 (나중에 User FK로 바꿔도 됨)
    clerk_user_id = models.CharField(max_length=255, db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id}: {self.title}"


