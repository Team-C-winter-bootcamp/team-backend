from django.contrib import admin
from django.urls import path, re_path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
    openapi.Info(
        title="Team Backend API",
        default_version='v1',
        description="팀 백엔드 API 명세서",
        # URL 설정이 중요합니다. 
        # prod.py의 PROTOCOL_SET: ['https']와 연동되어 작동합니다.
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

# config/urls.py (메인)
urlpatterns = [
    path('admin/', admin.site.urls),
    
    # 'api/v1/'을 제거하여 프론트엔드 요청 경로와 일치시킴
    path('cases/', include('cases.urls')),
    path('documents/', include('documents.urls')),
    
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('metrics/', include('django_prometheus.urls')),
]

# 개발 환경 정적 파일 (운영 환경은 WhiteNoise가 담당)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
