#!/usr/bin/env python3
"""
Core build/deploy pipeline for Phase 1.
Usage: python3 -m panel_app.pipeline <project-name> <git-url> <branch> [domain]
"""
import sys
import os
import subprocess
import time
import logging
import requests
from django.conf import settings
from celery import shared_task
from panel_app.models import Project, Deployment, Domain
from panel_app.docker_client import build_image, run_container, stop_project
from panel_app.dockerfile_generator import generate_dockerfile
from panel_app.caddy_client import update_caddy_route
from pathlib import Path

logger = logging.getLogger(__name__)

DEPLOYMENTS_DIR = Path('/home/tanvir/project/panel/deployments')
WORKSPACE_DIR = DEPLOYMENTS_DIR / 'workspace'

def deploy(project_name, git_url, branch='main', domain=None, base_domain='localhost'):
    workspace = WORKSPACE_DIR / project_name
    build_log_path = DEPLOYMENTS_DIR / 'logs' / f'{project_name}.log'
    
    logger.info(f"Deploying {project_name} from {git_url}")
    
    os.makedirs(workspace, exist_ok=True)
    if (workspace / '.git').exists():
        subprocess.run(['git', '-C', str(workspace), 'fetch', 'origin'], capture_output=True)
        subprocess.run(['git', '-C', str(workspace), 'reset', '--hard', f'origin/{branch}'], capture_output=True)
    else:
        result = subprocess.run(['git', 'clone', '--branch', branch, git_url, str(workspace)], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"Git clone failed: {result.stderr}")
            return False
    
    dockerfile = generate_dockerfile(workspace)
    (workspace / 'Dockerfile').write_text(dockerfile)
    
    from panel_app.models import Project
    project, _ = Project.objects.get_or_create(
        slug=project_name,
        defaults={
            'name': project_name,
            'git_repo_url': git_url,
            'git_branch': branch,
            'build_method': 'auto',
        }
    )
    
    commit_result = subprocess.run(['git', '-C', str(workspace), 'rev-parse', branch], capture_output=True, text=True)
    if commit_result.returncode != 0:
        commit_result = subprocess.run(['git', '-C', str(workspace), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    commit_sha = commit_result.stdout.strip()[:12]
    
    tag = f"{project_name}:{commit_sha}"
    image_tag, success = build_image(project, commit_sha, build_log_path)
    tag_to_use = image_tag if success else tag
    
    if not success:
        logger.error("Build failed")
        project.status = 'failed'
        project.save()
        return False
    
    stop_project(project)
    time.sleep(2)
    
    container_id, internal_port = run_container(project, tag_to_use, [])
    
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
        project.status = 'failed'
        project.save()
        logger.error("Health check failed")
        return False
    
    project.container_id = container_id
    project.internal_port = internal_port
    project.container_name = f"app-{project_name}"
    project.status = 'running'
    project.save()
    
    effective_domain = domain or f"{project_name}.{base_domain}"
    update_caddy_route(project, effective_domain)
    
    logger.info(f"Successfully deployed {project_name} at {effective_domain}")
    return True

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python3 -m panel_app.pipeline <project-name> <git-url> [branch] [domain]")
        sys.exit(1)
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dj_panel.settings')
    import django
    django.setup()
    
    project_name = sys.argv[1]
    git_url = sys.argv[2]
    branch = sys.argv[3] if len(sys.argv) > 3 else 'main'
    domain = sys.argv[4] if len(sys.argv) > 4 else None
    
    success = deploy(project_name, git_url, branch, domain)
    sys.exit(0 if success else 1)
