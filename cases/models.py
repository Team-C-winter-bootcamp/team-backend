from django.db import models


class Category(models.Model):
    """카테고리 테이블 (categories)"""
    # Django는 기본적으로 'id' 필드를 자동 생성하지만,
    # ERD에 맞춰 이름을 명시적으로 지정할 수도 있습니다.
    category_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, verbose_name="카테고리 이름")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Question(models.Model):
    """질문 테이블 (questions)"""
    question_id = models.AutoField(primary_key=True)
    # 카테고리와 1:N 관계
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


class Template(models.Model):
    TYPE_CHOICES = [
        ('고소장', '고소장'),
        ('내용증명', '내용증명'),
        ('합의서', '합의서'),
    ]

    template_id = models.AutoField(primary_key=True)
    # Enum 타입을 Django의 choices로 구현
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='고소장',
        verbose_name="템플릿 타입"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)