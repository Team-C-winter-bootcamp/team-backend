from django.urls import path
from .views import CaseSearchView

urlpatterns = [
    path('', CaseSearchView.as_view(), name='case_search'),
]
