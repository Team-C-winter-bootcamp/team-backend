import uuid
from django.db import models

class Template(models.Model):
    TYPE_CHOICES = [
        ('고소장', '고소장'),
        ('내용증명서', '내용증명서    '),
        ('합의서', '합의서'),
    ]

    template_id = models.AutoField(primary_key=True)
    type = models.CharField(
        max_length=100,
        choices=TYPE_CHOICES,
        default='고소장',
        verbose_name="템플릿 타입"
    )
    content = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)



class Document(models.Model):
    TYPE_CHOICES = [
        ('고소장', '고소장'),
        ('내용증명서', '내용증명서'),
        ('합의서', '합의서'),
    ]

    document_id = models.AutoField(primary_key=True)
    type = models.CharField(
        max_length=100,
        choices=TYPE_CHOICES,
        default='고소장',
        verbose_name="템플릿 타입"
    )
    content = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)




