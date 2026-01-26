from django.urls import path
from .views import ComplaintView, NoticeView, AgreementView

urlpatterns = [
    path('complaint/', ComplaintView.as_view(), name='complaint-api'),
    path('notice/', NoticeView.as_view(), name='notice-api'),
    path('agreement/', AgreementView.as_view(), name='agreement-api'),
]