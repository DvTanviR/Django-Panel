from django.urls import path
from . import github_app_views

urlpatterns = [
    path('connect/', github_app_views.github_connect, name='github_connect'),
    path('callback/', github_app_views.github_callback, name='github_callback'),
    path('repos/', github_app_views.github_repos, name='github_repos'),
    path('status/', github_app_views.github_status, name='github_status'),
    path('disconnect/', github_app_views.disconnect_github, name='disconnect_github'),
]
