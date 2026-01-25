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
        terms_of_service="<https://www.google.com/policies/terms/>",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/cases/', include('cases.urls')),

    # API docs
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('swagger', RedirectView.as_view(url='/swagger/', permanent=False), name='swagger-redirect'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    # Cases
    path('api/cases/', include('cases.urls')),
    path('api/documents/', include('documents.urls'))
]

# 개발 환경에서 정적 파일 및 미디어 파일 제공
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)