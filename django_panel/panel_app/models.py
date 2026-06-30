from django.db import models
from django.contrib.auth.models import User
from cryptography.fernet import Fernet
from django.conf import settings
import base64
import secrets
import string

def generate_slug():
    return ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(8))

class EncryptedTextField(models.TextField):
    description = "Stores encrypted text"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None:
            return value
        key = settings.ENCRYPTION_KEY
        if not key:
            return value
        try:
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.encrypt(value.encode()).decode()
        except Exception:
            return value
    
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        key = settings.ENCRYPTION_KEY
        if not key:
            return value
        try:
            f = Fernet(key.encode() if isinstance(key, str) else key)
            return f.decrypt(value.encode()).decode()
        except Exception:
            return value

class Project(models.Model):
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('building', 'Building'),
        ('deploying', 'Deploying'),
        ('failed', 'Failed'),
        ('never_deployed', 'Never Deployed'),
    ]
    
    BUILD_METHOD_CHOICES = [
        ('auto', 'Auto-detected'),
        ('dockerfile', 'Custom Dockerfile'),
        ('buildpack', 'Buildpack'),
    ]
    
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=50, unique=True, default=generate_slug)
    git_repo_url = models.URLField(max_length=500)
    git_branch = models.CharField(max_length=100, default='main')
    github_installation_id = models.CharField(max_length=100, blank=True, null=True)
    github_webhook_id = models.IntegerField(blank=True, null=True)
    root_directory = models.CharField(max_length=500, blank=True, default='')
    
    build_method = models.CharField(max_length=20, choices=BUILD_METHOD_CHOICES, default='auto')
    django_settings_module = models.CharField(max_length=255, blank=True, default='')
    wsgi_asgi = models.CharField(max_length=10, choices=[('wsgi', 'WSGI'), ('asgi', 'ASGI')], blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='never_deployed')
    container_id = models.CharField(max_length=100, blank=True, null=True)
    container_name = models.CharField(max_length=100, blank=True, null=True)
    internal_port = models.IntegerField(blank=True, null=True)
    last_deployed_at = models.DateTimeField(blank=True, null=True)
    
    cpu_limit = models.CharField(max_length=20, default='0.5')
    memory_limit = models.CharField(max_length=20, default='512m')
    
    is_current_deployment_id = models.IntegerField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name

class EnvironmentVariable(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environment_variables')
    key = models.CharField(max_length=255)
    value_encrypted = EncryptedTextField()
    is_secret = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['project', 'key']
        ordering = ['key']
    
    @property
    def value(self):
        return self.value_encrypted
    
    @value.setter
    def value(self, val):
        self.value_encrypted = val
    
    def __str__(self):
        return f"{self.project.slug}.{self.key}"

class Deployment(models.Model):
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('building', 'Building'),
        ('deploying', 'Deploying'),
        ('healthy', 'Healthy'),
        ('failed', 'Failed'),
        ('rolled_back', 'Rolled Back'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='deployments')
    git_commit_sha = models.CharField(max_length=40)
    git_commit_message = models.TextField(blank=True, default='')
    triggered_by = models.CharField(max_length=20, choices=[
        ('webhook', 'Webhook'),
        ('manual', 'Manual'),
        ('rollback', 'Rollback'),
    ])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    docker_image_tag = models.CharField(max_length=100)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(blank=True, null=True)
    build_log = models.TextField(blank=True, default='')
    is_current = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.project.slug}@{self.git_commit_sha[:8]}"

class Domain(models.Model):
    TLS_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('failed', 'Failed'),
    ]
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='domains')
    hostname = models.CharField(max_length=255)
    is_primary = models.BooleanField(default=False)
    dns_verified = models.BooleanField(default=False)
    tls_status = models.CharField(max_length=20, choices=TLS_STATUS_CHOICES, default='pending')
    verified_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['project', 'hostname']
        ordering = ['-is_primary', 'hostname']
    
    def __str__(self):
        return self.hostname

class WebhookEvent(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='webhook_events', blank=True, null=True)
    raw_payload = models.JSONField()
    processed_at = models.DateTimeField(blank=True, null=True)
    result = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Webhook {self.id}"
