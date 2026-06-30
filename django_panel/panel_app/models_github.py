from django.db import models
from django.contrib.auth.models import User

class GitHubAppConfig(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='github_app_config')
    app_id = models.CharField(max_length=100)
    installation_id = models.CharField(max_length=100, blank=True)
    private_key = models.TextField()
    client_id = models.CharField(max_length=100)
    client_secret = models.TextField()
    connected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "GitHub App Config"
        verbose_name_plural = "GitHub App Configs"
