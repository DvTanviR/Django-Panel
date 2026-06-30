import os
import subprocess
import time
import logging
import requests
from django.conf import settings
from celery import shared_task
from panel_app.models import Project, Deployment, Domain
from panel_app.docker_client import build_image, run_container, stop_project, check_crash_loop

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def deploy_project(self, project_id, deployment_id):
    from panel_app.caddy_client import update_caddy_route
    
    project = Project.objects.get(id=project_id)
    deployment = Deployment.objects.get(id=deployment_id, project=project)
    
    project.status = 'building'
    project.save()
    deployment.status = 'building'
    deployment.save(update_fields=['status'])
    
    workspace = settings.WORKSPACE_DIR / project.slug
    build_log_path = settings.LOGS_DIR / f"{project.slug}-{deployment.id}.log"
    
    os.makedirs(workspace, exist_ok=True)
    
    try:
        result = subprocess.run(
            ['git', 'clone', '--branch', project.git_branch, project.git_repo_url, str(workspace)],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode != 0:
            raise Exception(f"Git clone failed: {result.stderr}")
        
        result2 = subprocess.run(
            ['git', '-C', str(workspace), 'rev-parse', project.git_branch],
            capture_output=True, text=True
        )
        commit_sha = result2.stdout.strip()[:12]
        if not commit_sha:
            result2 = subprocess.run(
                ['git', '-C', str(workspace), 'rev-parse', 'HEAD'],
                capture_output=True, text=True
            )
            commit_sha = result2.stdout.strip()[:12]
        
        deployment.git_commit_sha = commit_sha
        deployment.save(update_fields=['git_commit_sha'])
        
    except Exception as e:
        logger.error(f"Clone error: {e}")
        deployment.status = 'failed'
        deployment.save(update_fields=['status'])
        project.status = 'failed'
        project.save()
        return
    
    image_tag, success = build_image(project, commit_sha, build_log_path)
    
    if not success:
        deployment.status = 'failed'
        deployment.save(update_fields=['status'])
        project.status = 'failed'
        project.save()
        return
    
    deployment.docker_image_tag = image_tag
    deployment.status = 'deploying'
    deployment.save(update_fields=['docker_image_tag', 'status'])
    project.status = 'deploying'
    project.save()
    
    env_vars = project.environment_variables.all()
    container_id, internal_port = run_container(project, image_tag, env_vars)
    
    health_url = f"http://localhost:{internal_port}/"
    healthy = False
    for i in range(30):
        try:
            r = requests.get(health_url, timeout=5)
            if r.status_code < 500:
                healthy = True
                break
        except Exception:
            pass
        time.sleep(2)
    
    if not healthy:
        stop_project(project)
        deployment.status = 'failed'
        deployment.save(update_fields=['status'])
        project.status = 'failed'
        project.save()
        return
    
    time.sleep(5)
    is_crash_looping, restart_count = check_crash_loop(project.container_name)
    if is_crash_looping:
        logger.warning(f"Project {project.slug} is crash-looping ({restart_count} restarts)")
        project.status = 'failed'
        project.save(update_fields=['status'])
        deployment.status = 'failed'
        deployment.save(update_fields=['status'])
        stop_project(project)
        return
    
    project.container_id = container_id
    project.internal_port = internal_port
    project.container_name = f"app-{project.slug}"
    project.status = 'running'
    project.last_deployed_at = deployment.started_at
    
    project.is_current_deployment_id = deployment.id
    project.save()
    
    primary_domain = project.domains.filter(is_primary=True).first()
    domain = primary_domain.hostname if primary_domain else f"{project.slug}.{settings.BASE_DOMAIN}"
    update_caddy_route(project, domain)
    
    deployment.status = 'healthy'
    deployment.is_current = True
    deployment.save(update_fields=['status', 'is_current'])
    
    Deployment.objects.filter(project=project).exclude(id=deployment.id).update(is_current=False)

@shared_task(bind=True)
def rollback_deployment(self, deployment_id):
    deployment = Deployment.objects.get(id=deployment_id)
    project = deployment.project
    
    deployment.status = 'deploying'
    deployment.triggered_by = 'rollback'
    deployment.save(update_fields=['status', 'triggered_by'])
    
    from panel_app.caddy_client import update_caddy_route
    
    stop_project(project)
    time.sleep(2)
    
    env_vars = project.environment_variables.all()
    container_id, internal_port = run_container(project, deployment.docker_image_tag, env_vars)
    
    project.container_id = container_id
    project.internal_port = internal_port
    project.status = 'running'
    project.is_current_deployment_id = deployment.id
    project.save()
    
    primary_domain = project.domains.filter(is_primary=True).first()
    domain = primary_domain.hostname if primary_domain else f"{project.slug}.{settings.BASE_DOMAIN}"
    update_caddy_route(project, domain)
    
    deployment.is_current = True
    deployment.status = 'healthy'
    deployment.save(update_fields=['is_current', 'status'])
    
    Deployment.objects.filter(project=project).exclude(id=deployment.id).update(is_current=False)
