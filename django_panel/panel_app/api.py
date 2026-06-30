from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Project, Deployment, Domain, EnvironmentVariable, WebhookEvent
from .serializers import ProjectSerializer, DeploymentSerializer, DomainSerializer, EnvironmentVariableSerializer
from .tasks import deploy_project, verify_domain_dns
from .github_service import GitHubService

class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    
    def perform_create(self, serializer):
        project = serializer.save()
        
        webhook_url = f"{settings.SERVER_IP}/api/webhooks/github/"
        if settings.BASE_DOMAIN != 'localhost':
            webhook_url = f"https://{settings.BASE_DOMAIN}/api/webhooks/github/"
        
        request = self.request
        access_token = request.session.get('github_access_token') if hasattr(request, 'session') else None
        
        success, result = GitHubService.register_webhook(
            project.git_repo_url,
            project.id,
            webhook_url,
            settings.GITHUB_WEBHOOK_SECRET,
            access_token
        )
        
        if success:
            project.github_webhook_id = result
            project.save(update_fields=['github_webhook_id'])
    
    @action(detail=True, methods=['get', 'post'])
    def deploy(self, request, pk=None):
        project = self.get_object()
        deploy = Deployment.objects.create(
            project=project,
            git_commit_sha='manual',
            git_commit_message='Manual deploy',
            triggered_by='manual',
            status='queued',
            docker_image_tag=f"{project.slug}:latest-manual",
        )
        project.status = 'building'
        project.save()
        deploy_project.delay(project.id, deploy.id)
        return Response(DeploymentSerializer(deploy).data)
    
    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        project = self.get_object()
        from .docker_client import stop_project
        stop_project(project)
        return Response({'status': 'stopped'})
    
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        project = self.get_object()
        from .docker_client import start_project
        start_project(project)
        return Response({'status': 'starting'})
    
    @action(detail=True, methods=['post'])
    def restart(self, request, pk=None):
        project = self.get_object()
        from .docker_client import restart_project
        restart_project(project)
        return Response({'status': 'restarting'})

class DeploymentViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeploymentSerializer
    
    def get_queryset(self):
        return Deployment.objects.all().order_by('-started_at')

class DomainViewSet(viewsets.ModelViewSet):
    serializer_class = DomainSerializer
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return Domain.objects.filter(project_id=project_id)
        return Domain.objects.all()
    
    def perform_destroy(self, instance):
        from .caddy_client import remove_caddy_domain
        remove_caddy_domain(instance.project, instance.hostname)
        super().perform_destroy(instance)
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        domain = self.get_object()
        verify_domain_dns.delay(domain.id)
        domain.dns_verified = False
        domain.save(update_fields=['dns_verified'])
        return Response({
            'status': 'verifying',
            'domain': domain.hostname,
            'message': 'DNS verification started. This may take a few minutes.'
        })

class EnvironmentVariableViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = EnvironmentVariableSerializer
    
    def get_queryset(self):
        project_id = self.request.query_params.get('project_id')
        if project_id:
            return EnvironmentVariable.objects.filter(project_id=project_id)
        return EnvironmentVariable.objects.all()

class WebhookEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookEvent.objects.all()
    serializer_class = WebhookEventSerializer
