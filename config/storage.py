"""
S3 커스텀 스토리지 클래스 - 판례내용 등 긴 텍스트 저장용
"""
from storages.backends.s3boto3 import S3Boto3Storage


class TextStorage(S3Boto3Storage):
    """긴 텍스트 저장용 S3 스토리지 (판례내용 등)"""
    location = "texts"
    default_acl = "private"
    file_overwrite = True
