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
    content = models.TextField(verbose_name="질문 내용")
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)
    # ERD에 질문의 is_deleted는 TIMESTAMP(NULL 가능)로 되어 있어 DateTimeField로 설정했습니다.
    is_deleted = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"[{self.category.name}] {self.content[:20]}"


class Case(models.Model):
    """사건 테이블 (cases)"""
    # ERD상 기본키 이름이 id입니다.
    id = models.AutoField(primary_key=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='cases'
    )
    # 사용자 상황 정보 (JSON 타입)
    user_info = models.JSONField(verbose_name="사용자 상황 정보")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)


class Template(models.Model):
    """문서 템플릿 테이블 (templates)"""
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
        verbose_name="템플릿 타입"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)