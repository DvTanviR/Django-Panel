from rest_framework import serializers
from .models import Project, Deployment, Domain, EnvironmentVariable, WebhookEvent

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = '__all__'
        read_only_fields = ['slug', 'status', 'container_id', 'container_name', 'internal_port', 'last_deployed_at', 'is_current_deployment_id', 'created_at', 'updated_at']

class DeploymentSerializer(serializers.ModelSerializer):
    project_name = serializers.CharField(source='project.name', read_only=True)
    
    class Meta:
        model = Deployment
        fields = '__all__'
        read_only_fields = ['git_commit_sha', 'git_commit_message', 'triggered_by', 'started_at', 'finished_at', 'build_log', 'is_current']

class DomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = Domain
        fields = '__all__'
        read_only_fields = ['dns_verified', 'tls_status', 'verified_at', 'created_at']

class EnvironmentVariableSerializer(serializers.ModelSerializer):
    class Meta:
        model = EnvironmentVariable
        fields = ['id', 'project', 'key', 'is_secret', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']

class WebhookEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = WebhookEvent
        fields = '__all__'
        read_only_fields = ['created_at']
