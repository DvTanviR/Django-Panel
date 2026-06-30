import os
import re
from pathlib import Path

DOCKERFILE_TEMPLATE = """FROM python:{python_version}-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    libpq-dev \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
{env_overrides}

CMD {cmd}
"""

def detect_python_version(workspace):
    for f in ['.python-version', 'runtime.txt']:
        p = workspace / f
        if p.exists():
            content = p.read_text().strip()
            m = re.search(r'(\d+\.\d+)', content)
            if m:
                return m.group(1)
    
    pyproject = workspace / 'pyproject.toml'
    if pyproject.exists():
        content = pyproject.read_text()
        m = re.search(r'requires-python\s*=\s*["\']([^"\']+)["\']', content)
        if m:
            if '>=3.11' in m.group(1) or '>=3.12' in m.group(1):
                return '3.12'
            if '>=3.10' in m.group(1):
                return '3.11'
            if '>=3.9' in m.group(1):
                return '3.10'
    return '3.12'

def detect_dependency_manager(workspace):
    if (workspace / 'requirements.txt').exists():
        return 'pip'
    if (workspace / 'poetry.lock').exists():
        return 'poetry'
    if (workspace / 'Pipfile.lock').exists():
        return 'pipenv'
    if (workspace / 'pyproject.toml').exists():
        return 'poetry'
    return 'pip'

def detect_project_type(workspace):
    has_manage_py = (workspace / 'manage.py').exists()
    has_celery = False
    for req_file in ['requirements.txt', 'pyproject.toml']:
        p = workspace / req_file
        if p.exists():
            content = p.read_text().lower()
            if 'celery' in content:
                has_celery = True
    return has_manage_py, has_celery

def generate_dockerfile(workspace, project=None):
    python_version = detect_python_version(workspace)
    dep_manager = detect_dependency_manager(workspace)
    has_manage_py, has_celery = detect_project_type(workspace)
    
    install_cmd = "pip install --no-cache-dir -r requirements.txt"
    copy_cmd = "COPY requirements.txt ./"
    copy_project = "COPY . ."
    
    if dep_manager == 'poetry':
        install_cmd = "poetry install --no-root --no-dev"
    
    collectstatic = ""
    if has_manage_py:
        collectstatic = "RUN python manage.py collectstatic --noinput || true\n"
    
    if has_manage_py:
        wsgi_asgi = 'wsgi'
        cmd = f"gunicorn project.wsgi:application --bind 0.0.0.0:8000 --workers 4"
    else:
        cmd = "python -m uvicorn main:app --host 0.0.0.0 --port 8000"
    
    env_overrides = ""
    if project and project.django_settings_module:
        env_overrides = f"ENV DJANGO_SETTINGS_MODULE={project.django_settings_module}"
    
    dockerfile = f"""FROM python:{python_version}-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \\
    gcc \\
    libpq-dev \\
    build-essential \\
    curl \\
    && rm -rf /var/lib/apt/lists/*

{copy_cmd}
RUN {install_cmd}

{copy_project}
{collectstatic}
{env_overrides}

EXPOSE 8000

CMD {cmd}
"""
    return dockerfile
