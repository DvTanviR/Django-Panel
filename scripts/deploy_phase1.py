#!/usr/bin/env python3
"""
Standalone Phase 1 deploy pipeline.
No Django required - pure docker-py + subprocess.
Usage: ./deploy.sh <project-name> <git-url> [branch] [domain]
"""
import sys
import os
import subprocess
import time
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DEPLOYMENTS_DIR = '/home/tanvir/project/panel/deployments'
WORKSPACE_DIR = f'{DEPLOYMENTS_DIR}/workspace'
LOGS_DIR = f'{DEPLOYMENTS_DIR}/logs'

os.makedirs(WORKSPACE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

def run(cmd, check=True, capture=True):
    r = subprocess.run(cmd, shell=False, capture_output=capture, text=True)
    if check and r.returncode != 0:
        logger.error(f"Command failed: {' '.join(cmd)}")
        logger.error(r.stderr)
        raise RuntimeError(f"Command failed: {' '.join(cmd)}")
    return r

def clone_repo(workspace, git_url, branch):
    if os.path.exists(os.path.join(workspace, '.git')):
        logger.info("Repo exists, fetching latest...")
        run(['git', '-C', workspace, 'fetch', 'origin'])
        run(['git', '-C', workspace, 'reset', '--hard', f'origin/{branch}'])
    else:
        logger.info(f"Cloning {git_url}...")
        run(['git', 'clone', '--branch', branch, git_url, workspace])
    logger.info("Clone complete")

def generate_dockerfile(workspace):
    requirements = None
    req_path = os.path.join(workspace, 'requirements.txt')
    if os.path.exists(req_path):
        requirements = open(req_path).read().strip()
    
    dockerfile = """FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    libpq-dev \\
    build-essential \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1

CMD gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 4
"""
    return dockerfile

def build_image(workspace, tag, log_path):
    import docker
    client = docker.from_env()
    log_file = open(log_path, 'w')
    try:
        dockerfile = generate_dockerfile(workspace)
        with open(os.path.join(workspace, 'Dockerfile'), 'w') as f:
            f.write(dockerfile)
        
        image, logs = client.images.build(path=workspace, tag=tag, rm=True)
        for line in logs:
            if 'stream' in line:
                log_file.write(line['stream'])
        log_file.write(f"\nBuilt: {tag}\n")
        return image, True
    except Exception as e:
        log_file.write(f"\nBuild failed: {e}\n")
        return None, False
    finally:
        log_file.close()

def run_container(tag, project_name, mem_limit='512m', cpu_quota=50000, cpu_period=100000):
    import docker
    client = docker.from_env()
    
    container_name = f"app-{project_name}"
    
    existing = client.containers.list(all=True, filters={'name': container_name})
    for c in existing:
        try:
            c.remove(force=True)
        except Exception:
            pass
    
    container = client.containers.run(
        tag,
        name=container_name,
        detach=True,
        restart_policy={'Name': 'unless-stopped'},
        mem_limit=mem_limit,
        nano_cpus=cpu_quota,
        ports={'8000/tcp': None},
    )
    
    time.sleep(3)
    container.reload()
    
    port = None
    try:
        ports = container.attrs['NetworkSettings']['Ports']
        if '8000/tcp' in ports and ports['8000/tcp']:
            port = int(ports['8000/tcp'][0]['HostPort'])
    except Exception:
        pass
    
    return container.id, port

def health_check(port, timeout=60):
    import requests
    url = f"http://localhost:{port}/"
    for i in range(timeout):
        try:
            r = requests.get(url, timeout=3)
            if r.status_code < 500:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False

def stop_container(container_id):
    import docker
    client = docker.from_env()
    try:
        c = client.containers.get(container_id)
        c.stop()
        c.remove()
        logger.info(f"Stopped container {container_id[:12]}")
    except Exception as e:
        logger.warning(f"Could not stop container: {e}")

def update_caddy(project_name, domain, port, base_domain='apps.localhost', https_port='8443', http_port='8080'):
    import requests
    caddy_api = 'http://localhost:2019'
    
    upstream = f"localhost:{port}"
    config = {
        "admin": {"enabled": True, "listen": "0.0.0.0:2019"},
        "storage": {"module": "file_system", "root": "/data"},
        "apps": {
            "http": {
                "servers": {
                    base_domain: {
                        "listen": [f":{https_port}", f":{http_port}"],
                        "routes": [
                            {
                                "match": [{"host": [domain]}],
                                "handle": [
                                    {
                                        "handler": "reverse_proxy",
                                        "upstreams": [{"dial": upstream}],
                                        "transport": {"protocol": "http"}
                                    }
                                ]
                            }
                        ]
                    }
                }
            }
        }
    }
    
    try:
        r = requests.post(f"{caddy_api}/load", json=config, timeout=10)
        if r.status_code == 200:
            logger.info(f"Caddy route updated: {domain} -> {upstream}")
            return True
        else:
            logger.error(f"Caddy load failed: {r.status_code} {r.text}")
            return False
    except Exception as e:
        logger.error(f"Caddy error: {e}")
        return False

def deploy(project_name, git_url, branch='main', domain=None, base_domain='localhost', mem_limit='512m'):
    workspace = os.path.join(WORKSPACE_DIR, project_name)
    log_path = os.path.join(LOGS_DIR, f'{project_name}-build.log')
    tag = f"{project_name}:latest"
    
    try:
        clone_repo(workspace, git_url, branch)
        
        logger.info("Building Docker image...")
        image, success = build_image(workspace, tag, log_path)
        if not success:
            logger.error("Build failed")
            return False
        
        logger.info("Running container...")
        container_id, port = run_container(tag, project_name, mem_limit)
        if port is None:
            logger.error("Could not determine container port")
            stop_container(container_id)
            return False
        
        logger.info(f"Container running on port {port}")
        
        logger.info("Health checking...")
        if not health_check(port):
            logger.error("Health check failed")
            stop_container(container_id)
            return False
        
        effective_domain = domain or f"{project_name}.{base_domain}"
        update_caddy(project_name, effective_domain, port, base_domain)
        
        logger.info(f"SUCCESS: {project_name} deployed to {effective_domain}")
        return True
        
    except Exception as e:
        logger.error(f"Deploy failed: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <project-name> <git-url> [branch] [domain]")
        sys.exit(1)
    
    project_name = sys.argv[1]
    git_url = sys.argv[2]
    branch = sys.argv[3] if len(sys.argv) > 3 else 'main'
    domain = sys.argv[4] if len(sys.argv) > 4 else None
    
    success = deploy(project_name, git_url, branch, domain)
    sys.exit(0 if success else 1)
