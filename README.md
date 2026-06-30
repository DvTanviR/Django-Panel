# DeployDjango

Self-hosted PaaS for Django applications. Deploy Django apps from GitHub with one click, zero-downtime deploys, custom domains with automatic TLS, and isolated containers.

## What's Built

- **Phase 1**: Core build/deploy pipeline (clone, Dockerfile auto-gen, build, run, health-check, Caddy route)
- **Phase 2**: Django control plane with full data models (Project, Deployment, Domain, EnvironmentVariable, WebhookEvent)
- **Phase 4**: Next.js + Tailwind GUI dashboard (project list, deploy button, logs, env vars, domains)
- **Phase 6**: `install.sh` / `uninstall.sh` scripts for Ubuntu

## Tech Stack

- **Backend**: Django + DRF (Python 3.12)
- **Database**: PostgreSQL (Dockerized)
- **Queue**: Celery + Redis (Dockerized)
- **Frontend**: Next.js 14 + Tailwind CSS
- **Proxy**: Caddy v2 with Admin API
- **Runtime**: Docker Engine via docker-py

## Quick Start (Development)

```bash
cd panel
docker compose up -d
docker compose exec django python manage.py migrate
docker compose exec django python manage.py panel_app createadmin --username admin --password admin123
```

- Django API: http://localhost:8000
- Frontend dev: `cd frontend && npm install && npm run dev` (http://localhost:3000)

## Quick Start (Production)

```bash
sudo ./install.sh
```

## Architecture

```
┌─────────────────────────────────────┐
│           Caddy v2 (Port 80/443)    │
│    Reverse Proxy + Auto TLS         │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Django Control Plane (API)     │
│   - Project Management              │
│   - Build/Deploy Orchestration      │
│   - Webhook Handler                 │
└──────────────┬──────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────┐         ┌─────▼─────┐
│ Celery │         │   Redis   │
│ Worker │         │   Queue   │
└───┬────┘         └───────────┘
    │
    ├─── Clone Repo ────► Build Docker Image
    ├─── Run Container ──► Health Check
    ├─── Update Caddy ──► Route Traffic
    └─── Store Metadata in Postgres
```

## Data Model

- **Project**: name, slug, repo URL, branch, status, resource limits
- **Deployment**: commit SHA, status, image tag, build log, rollback support
- **Domain**: hostname, DNS verification status, TLS status
- **EnvironmentVariable**: encrypted at rest, secret masking in UI
- **WebhookEvent**: audit trail of GitHub events

## Build Pipeline

```
Trigger (Webhook/Manual)
    ↓
Clone Repo (isolated workspace)
    ↓
Detect Framework (manage.py, requirements, Python version)
    ↓
Generate Dockerfile (if not in repo)
    ↓
Build Image (stream logs to UI)
    ↓
Run Container (with env vars + resource limits)
    ↓
Health Check (HTTP GET /, timeout 60s)
    ↓
Update Caddy Route (zero-downtime swap)
    ↓
Mark Deployment Healthy
```

## Dockerfile Auto-Generation

When no Dockerfile exists:
1. Detect Python version from `.python-version`, `runtime.txt`, or `pyproject.toml`
2. Install common system deps: `gcc`, `libpq-dev`, `build-essential`
3. Install Python dependencies via `pip` or `poetry`
4. Run `collectstatic --noinput` (gracefully)
5. Detect WSGI/ASGI entrypoint
6. Default CMD: `gunicorn` with configurable workers

## Domain + TLS Flow

1. Admin enters `app.example.com`
2. Panel shows DNS record (A/CNAME) with copy button
3. Background task polls DNS until verified
4. Caddy Admin API registers the route
5. Let's Encrypt certificate auto-provisioned on first request
6. TLS status reflected in GUI

## Security

- All secrets encrypted at rest using Fernet (custom EncryptedTextField)
- GitHub webhook HMAC signature verification
- Build containers have no access to host Docker socket
- DRF permissions on all endpoints
- Resource limits (CPU/memory) on every user container
- Django auth with token auth for API

## Roadmap

- [x] Phase 1: Core build/deploy pipeline
- [x] Phase 2: Django control plane + data models
- [x] Phase 3: GitHub App integration (OAuth + webhooks)
- [x] Phase 4: Next.js GUI dashboard
- [x] Phase 5: Custom domains + TLS
- [x] Phase 6: Production installer (tested on clean Ubuntu)
- [ ] Phase 7: Security hardening + CLI tool + documentation

## License

MIT
# Django-Panel
