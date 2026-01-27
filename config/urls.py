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

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Swagger & Redoc
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API v1 (프론트엔드 요청 경로와 일치시켜주세요)
    path('api/v1/cases/', include('cases.urls')),
    path('api/v1/documents/', include('documents.urls')),
    
    # Prometheus Metrics
    path('metrics/', include('django_prometheus.urls')),
]

# 개발 환경 정적 파일 (운영 환경은 WhiteNoise가 담당)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
