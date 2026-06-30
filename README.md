# DeployDjango

Self-hosted PaaS for Django applications. Deploy Django apps from GitHub with one click, zero-downtime deploys, custom domains with automatic TLS, and isolated containers.

## What's Built

- **Phase 1**: Core build/deploy pipeline (clone, Dockerfile auto-gen, build, run, health-check, Caddy route)
- **Phase 2**: Django control plane with full data models (Project, Deployment, Domain, EnvironmentVariable, WebhookEvent)
- **Phase 3**: GitHub App integration (OAuth + webhook auto-registration)
- **Phase 4**: Next.js + Tailwind GUI dashboard (project list, deploy button, logs, env vars, domains)
- **Phase 5**: Custom domains + TLS (DNS verification, Let's Encrypt via Caddy)
- **Phase 6**: Production installer (`install.sh` / `uninstall.sh`)
- **Phase 7**: CLI tool (`djpaas`), rate limiting, crash-loop detection, Dockerfile validation

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

## CLI Tool

The `djpaas` command is installed to `/usr/local/bin` during setup.

```bash
# Show all projects and their status
djpaas status

# Deploy a project manually
djpaas deploy <project-slug>

# Restart a running project
djpaas restart <project-slug>

# Stop/start a project
djpaas stop <project-slug>
djpaas start <project-slug>

# Tail logs
djpaas logs <project-slug>
djpaas logs <project-slug> --tail 100

# Upgrade the platform (pull new images, recreate containers)
djpaas upgrade

# Save API credentials for CLI
djpaas login
```

## Architecture

```
                            Internet
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Caddy v2         │
                    │  Port 80 / 443       │
                    │  Reverse Proxy       │
                    │  Auto TLS            │
                    │  Dynamic Routes      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │  Django Control Plane│
                    │  (DRF + Celery)      │
                    │                      │
                    │  Project Management  │
                    │  Build/Deploy        │
                    │  Webhook Handler     │
                    │  Domain Manager      │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌─────────┐     ┌─────────┐     ┌─────────┐
        │ Celery  │     │  Redis  │     │Postgres │
        │ Worker  │     │  Queue  │     │   DB    │
        └────┬────┘     └─────────┘     └─────────┘
             │
             ▼
    ┌─────────────────────────┐
    │  User App Containers     │
    │  (Docker, isolated,      │
    │   resource-limited)      │
    │                          │
    │  app-<slug>.localhost    │
    │  via Caddy               │
    └─────────────────────────┘
```

```
┌─────────────────────────────────────────────────────────────┐
│                    VPS / Single Server                        │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                  Docker Network (bridge)                  │ │
│  │                                                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │ │
│  │  │  Caddy   │  │  Django  │  │  Celery  │  │  Redis │ │ │
│  │  │  :80/:443│  │  :8000   │  │  Worker  │  │  :6379 │ │ │
│  │  │  :2019   │  │          │  │          │  │        │ │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───┬────┘ │ │
│  │       │             │             │             │      │ │
│  │       │    ┌────────▼─────────────▼────────┐    │      │ │
│  │       │    │      PostgreSQL :5432         │    │      │ │
│  │       │    └───────────────────────────────┘    │      │ │
│  │       │                                        │      │ │
│  │  ┌────▼─────────────────────────────────────────┐│      │ │
│  │  │   /var/run/docker.sock                       ││      │ │
│  │  │   (Docker Engine - mounts into Django)       ││      │ │
│  │  └───────────────────────────────────────────────┘│      │ │
│  │                                                    │      │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │      │ │
│  │  │ User App │  │ User App │  │ User App │  ...    │      │ │
│  │  │ Container│  │ Container│  │ Container │         │      │ │
│  │  │  :8000   │  │  :8001   │  │  :8002    │         │      │ │
│  │  └──────────┘  └──────────┘  └──────────┘         │      │ │
│  └─────────────────────────────────────────────────────────┘ │
    └───────────────────────────────────────────────────────────┘
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
- [x] Phase 7: Security hardening + CLI tool + documentation

## CLI Tool

The `djpaas` command is installed to `/usr/local/bin` during setup.

```bash
djpaas status
djpaas deploy <project-slug>
djpaas restart <project-slug>
djpaas stop <project-slug>
djpaas start <project-slug>
djpaas logs <project-slug>
djpaas logs <project-slug> --tail 100
djpaas upgrade
djpaas login
```

## Troubleshooting

**Build fails with "No module named 'psycopg2'"**
- Ensure `libpq-dev` is installed. The auto-generated Dockerfile includes it by default.

**Health check fails after deploy**
- Check that your Django app binds to `0.0.0.0:8000`
- Verify `ALLOWED_HOSTS` includes the incoming Host header
- Check container logs: `docker logs app-<slug> --follow`

**Caddy returns 404**
- Verify the Caddy Admin API is reachable: `curl http://localhost:2019/config/`
- Check that the domain route is registered in Caddy config

**Webhook not triggering deploys**
- Verify webhook is registered in GitHub repo settings
- Check the webhook secret matches `GITHUB_WEBHOOK_SECRET` in `.env`

**Celery tasks not running**
- Check Redis: `docker compose exec redis redis-cli ping`
- Verify Celery logs: `docker compose logs celery`

**Permission denied on `.env`**
- Re-run install script as root, or: `sudo chmod 600 .env`

### Log Locations

- Platform logs: `docker compose -f docker/docker-compose.platform.yml logs -f django`
- Celery logs: `docker compose -f docker/docker-compose.platform.yml logs -f celery`
- User app logs: `docker logs app-<project-slug> --follow`
- Caddy logs: `docker logs panel-caddy --follow`

### Reset

```bash
sudo ./uninstall.sh    # stops containers, optionally wipes volumes
docker volume prune -f # remove Docker volumes
```

## License

MIT
# Django-Panel
