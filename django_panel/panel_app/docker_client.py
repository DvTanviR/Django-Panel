import docker
import os
import time
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

_client = None

def get_docker_client():
    global _client
    if _client is None:
        _client = docker.DockerClient(base_url='unix://' + settings.DOCKER_SOCKET)
    return _client

def build_image(project, commit_sha, build_log_path):
    from .dockerfile_validator import validate_dockerfile
    client = get_docker_client()
    tag = f"{project.slug}:{commit_sha[:12]}"
    workspace = settings.WORKSPACE_DIR / project.slug
    dockerfile_path = workspace / 'Dockerfile'
    
    log_file = open(build_log_path, 'w')
    
    try:
        if not dockerfile_path.exists():
            from .dockerfile_generator import generate_dockerfile
            dockerfile_content = generate_dockerfile(workspace, project)
            dockerfile_path.write_text(dockerfile_content)
            log_file.write("Generated Dockerfile\n")
        else:
            log_file.write("Using existing Dockerfile\n")
        
        if project.build_method == 'auto' or not dockerfile_path.exists():
            content = dockerfile_path.read_text()
            validate_dockerfile(content)
        
        client.images.build(
            path=str(workspace),
            tag=tag,
            rm=True,
            nocache=False,
        )
        log_file.write(f"Successfully built {tag}\n")
        return tag, True
    except Exception as e:
        log_file.write(f"Build failed: {str(e)}\n")
        return None, False
    finally:
        log_file.close()

def run_container(project, image_tag, env_vars):
    client = get_docker_client()
    container_name = f"app-{project.slug}"
    
    internal_port = 8000
    port_mapping = {'8000/tcp': None}
    
    env_list = {f"{ev.key}={ev.value}" for ev in project.environment_variables.all()}
    
    try:
        existing = client.containers.list(filters={'name': container_name}, all=True)
        for c in existing:
            c.remove(force=True)
    except Exception:
        pass
    
    container = client.containers.run(
        image_tag,
        name=container_name,
        ports=port_mapping,
        environment=env_list,
        detach=True,
        restart_policy={'Name': 'unless-stopped'},
        mem_limit=project.memory_limit,
        nano_cpus=int(float(project.cpu_limit) * 1e9),
        network='bridge',
    )
    
    time.sleep(2)
    container.reload()
    
    actual_port = None
    try:
        net = container.attrs['NetworkSettings']['Ports']
        if '8000/tcp' in net and net['8000/tcp']:
            actual_port = int(net['8000/tcp'][0]['HostPort'])
    except (KeyError, IndexError, TypeError):
        pass
    
    return container.id, actual_port

def stop_project(project):
    client = get_docker_client()
    container_name = f"app-{project.slug}"
    try:
        container = client.containers.get(container_name)
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass
    except Exception as e:
        logger.error(f"Error stopping {container_name}: {e}")

def start_project(project):
    from .tasks import deploy_project
    last_deploy = project.deployments.filter(is_current=True).first() or project.deployments.last()
    if last_deploy:
        from panel_app.models import Deployment
        deploy = Deployment.objects.create(
            project=project,
            git_commit_sha=last_deploy.git_commit_sha,
            git_commit_message='Restart',
            triggered_by='manual',
            status='deploying',
            docker_image_tag=last_deploy.docker_image_tag,
        )
        deploy_project(project.id, deploy.id)

def check_crash_loop(container_name, window_seconds=600, max_restarts=5):
    client = get_docker_client()
    try:
        container = client.containers.get(container_name)
        history = container.attrs['RestartCount']
        started_at = container.attrs['State']['StartedAt']
        
        # Simple check: if restarted many times recently
        if history >= max_restarts:
            return True, history
    except Exception:
        pass
    return False, 0

def get_container_stats(container_name):
    client = get_docker_client()
    try:
        container = client.containers.get(container_name)
        stats = container.stats(stream=False)
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        cpu_percent = (cpu_delta / system_delta) * 100.0 if system_delta > 0 else 0
        
        mem_usage = stats['memory_stats']['usage']
        mem_limit = stats['memory_stats']['limit']
        mem_percent = (mem_usage / mem_limit) * 100.0 if mem_limit > 0 else 0
        
        return {
            'cpu_percent': round(cpu_percent, 2),
            'memory_percent': round(mem_percent, 2),
            'memory_usage_mb': round(mem_usage / 1024 / 1024, 2),
            'restart_count': container.attrs['RestartCount'],
        }
    except Exception:
        return None
