from django.db import models


class Category(models.Model):
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name="카테고리 이름")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Question(models.Model):
    question_id = models.AutoField(primary_key=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='questions'
    )
    TYPE_CHOICES = [
        ('who', 'who'),
        ('when', 'when'),
        ('what', 'what'),
        ('want', 'want'),
    ]
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='what',
        verbose_name="질문 타입"
    )
    content = models.TextField(default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"[{self.category.name}] {self.content[:20]}"


class Case(models.Model):
    """사건 테이블 (cases)"""
    id = models.AutoField(primary_key=True)

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='cases'
    )

    who = models.CharField(max_length=255, default='', verbose_name="누구와")
    when = models.CharField(max_length=255, default='', verbose_name="언제")
    what = models.TextField(default='', verbose_name="무슨 일이")
    want = models.TextField(default='', verbose_name="원하는 결과")
    detail = models.TextField(default='', verbose_name="상세 내용")

    # 공통 필드
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

