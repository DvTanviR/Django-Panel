from django.urls import path
from . import github_views

urlpatterns = [
    path('push/', github_views.github_webhook, name='github_webhook'),
]
