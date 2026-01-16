from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager


class UserManager(BaseUserManager):
    """User 모델을 위한 커스텀 매니저"""
    
    def create_user(self, clerk_id, email=None, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not clerk_id:
            raise ValueError('clerk_id는 필수입니다.')
        
        user = self.model(clerk_id=clerk_id, email=email, **extra_fields)
        # Clerk를 사용하므로 password는 사용 불가능한 값으로 설정
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user
    
    def create_superuser(self, clerk_id, email=None, password=None, **extra_fields):
        """슈퍼유저 생성 (관리자용)"""
        # 슈퍼유저는 is_staff와 is_superuser를 True로 설정
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        # 슈퍼유저도 password를 설정할 수 있도록 함
        if password is None:
            password = 'admin123'  # 기본 비밀번호 (Clerk를 사용하므로 실제로는 사용되지 않음)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('슈퍼유저는 is_staff=True여야 합니다.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('슈퍼유저는 is_superuser=True여야 합니다.')
        
        return self.create_user(clerk_id, email, password, **extra_fields)


class User(AbstractBaseUser):
    """
    Clerk 사용자 정보와 동기화되는 모델
    """
    clerk_id = models.CharField(max_length=255, unique=True, help_text="Clerk User ID")
    email = models.EmailField(max_length=50, unique=True, null=True, blank=True)
    # password 필드는 Clerk에서 인증을 처리하므로 사용하지 않습니다.
    # AbstractBaseUser의 password 필드는 상속되지만 사용하지 않습니다.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    
    # Admin 접근을 위한 필드
    is_staff = models.BooleanField(default=False, help_text="Admin 사이트 접근 권한")
    is_superuser = models.BooleanField(default=False, help_text="모든 권한을 가진 슈퍼유저")

    objects = UserManager()

    USERNAME_FIELD = 'clerk_id'
    REQUIRED_FIELDS = ['email']  # createsuperuser 시 필요한 필드

    def __str__(self):
        return self.email or self.clerk_id
    
    def has_perm(self, perm, obj=None):
        """슈퍼유저는 모든 권한을 가집니다."""
        return self.is_superuser
    
    def has_module_perms(self, app_label):
        """슈퍼유저는 모든 앱에 접근할 수 있습니다."""
        return self.is_superuser

    class Meta:
        verbose_name = "사용자"
        verbose_name_plural = "사용자 목록"
        ordering = ["-created_at"]