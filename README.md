# DeployDjango

Self-hosted PaaS for Django. Deploy Django apps from GitHub in one click. Zero-downtime. Custom domains with automatic TLS. Isolated containers.

## One-Command Install

On a **fresh Ubuntu 20.04/22.04/24.04 VPS** with root access, run:

```bash
curl -fsSL https://raw.githubusercontent.com/DvTanviR/Django-Panel/main/install.sh | sudo bash
```

Or clone and run locally:

```bash
git clone https://github.com/DvTanviR/Django-Panel.git
cd Django-Panel
sudo ./install.sh
```

The installer does everything automatically:
1. Detects Ubuntu version
2. Installs Docker + Docker Compose if missing
3. Generates secure secrets (`.env`)
4. Starts all platform services (Caddy, PostgreSQL, Redis, Django, Celery)
5. Runs database migrations
6. Creates the admin user
7. Installs the `djpaas` CLI to `/usr/local/bin`

**Requirements:** Ubuntu 20.04/22.04/24.04, 2GB+ RAM, root/sudo access.

---

## First Login

After install finishes, open your browser:

```
http://YOUR-SERVER-IP:9000
```

Login with:
- **Username:** `admin`
- **Password:** `admin123`

You'll see the dashboard with no projects yet.

---

## Deploy Your First Django App (3 Steps)

### Step 1: Connect GitHub
1. Click **"New Project"** in the sidebar
2. Click **"Connect GitHub"** and authorize the app
3. Pick a repo from the list (or enter a Git URL manually)

### Step 2: Create Project
1. After selecting a repo, the **Project Name** and **Branch** auto-fill
2. Click **"Create Project"**

### Step 3: Deploy
1. You land on the project detail page
2. Click **"Deploy Now"**
3. Watch the build log stream in real time
4. When status turns **green**, your app is live

Your app is reachable at:
```
http://<project-slug>.apps.localhost:8080
```

---

## Using the GUI

### Project Dashboard
- **Dashboard** (sidebar): See all projects, their status, last deploy time
- **Project Detail**: Click any project card to see deployments, domains, env vars

### Deployments
Each project page shows:
- Deploy history (commit SHA, message, status)
- One-click **Rollback** to any previous deployment

### Domains
- Add a custom domain (e.g. `myapp.example.com`)
- Panel shows the DNS record (A record) you need to add
- Click **Verify** once DNS is set — panel auto-obtains Let's Encrypt TLS

### Environment Variables
- Add `DATABASE_URL`, `SECRET_KEY`, etc. per project
- Mark as **Secret** to mask values in the UI
- Values are encrypted at rest in the database

### Actions
- **Deploy Now**: Trigger a fresh build + deploy
- **Stop / Start / Restart**: Control the running container

---

## CLI Tool

`djpaas` is installed globally during setup.

```bash
# Show all projects
djpaas status

# Deploy a specific project
djpaas deploy myapp

# Tail live logs
djpaas logs myapp --tail 100

# Restart
djpaas restart myapp

# Upgrade platform (pull new images, recreate containers)
djpaas upgrade

# Save API token for CLI
djpaas login
```

---

## What Gets Installed

Everything runs in Docker containers on your VPS:

| Service | Purpose | Port |
|---------|---------|------|
| **DeployDjango Panel** | Control plane / GUI | **9000** |
| Caddy | Reverse proxy + auto TLS for apps | **8080** (HTTP) / **8443** (HTTPS) |
| PostgreSQL | Metadata database | 5432 |
| Redis | Task queue | 6379 |
| Celery | Async build/deploy worker | — |

Your Django apps each run in **their own isolated container** and are routed through Caddy on ports **8080/8443** — completely separate from the panel on port **9000**.

### Why Not Port 80/443?

If you already run websites (Node.js, other Django apps, etc.) on port **80/443**, DeployDjango uses **different ports** so nothing conflicts:

- Panel UI → `http://your-vps-ip:9000`
- Deployed apps → `http://app-name.apps.localhost:8080` (or your custom domain on 8080/8443)
- HTTPS apps → `https://app-name.yourdomain.com:8443`

You can change these ports anytime in `/opt/deploydjango/.env`:

```env
PANEL_PORT=9000
CADDY_HTTP_PORT=8080
CADDY_HTTPS_PORT=8443
BASE_DOMAIN=apps.localhost
```

---

## Directory Structure

```
/opt/deploydjango/          # Install location
├── django_panel/           # Django control plane
│   └── panel_app/          # Core app (models, API, tasks)
├── frontend/               # Next.js dashboard
├── docker/                 # Compose files + Dockerfiles
├── scripts/                # deploy_phase1.py + djpaas CLI
├── deployments/            # Build logs, workspaces
├── .env                    # Auto-generated secrets
├── docker-compose.yml      # Dev / local compose
└── docker/docker-compose.platform.yml  # Production compose
```

---

## Architecture

```
                            Internet
                               │
                               ▼
                    ┌──────────────────────┐
                    │     Caddy v2         │
                    │  Port 8080 / 8443    │
                    │  Reverse Proxy       │
                    │  Auto TLS            │
                    │  Dynamic Routes      │
                    └──────────┬───────────┘
                               │
                     ┌─────────▼─────────────────┐
                     │    Django Control Plane   │
                     │    http://vps:9000        │
                     │    (DRF + Celery)         │
                     │                          │
                     │  Project Management      │
                     │  Build/Deploy            │
                     │  Webhook Handler         │
                     │  Domain Manager          │
                     └──────────┬───────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
        ┌──────────┐     ┌──────────┐     ┌──────────┐
        │  Celery  │     │  Redis   │     │Postgres  │
        │  Worker  │     │  Queue   │     │   DB     │
        └────┬─────┘     └──────────┘     └──────────┘
```

---

## Data Model

- **Project**: name, slug, repo URL, branch, status, resource limits
- **Deployment**: commit SHA, status, image tag, build log, rollback support
- **Domain**: hostname, DNS verification status, TLS status
- **EnvironmentVariable**: encrypted at rest, secret masking in UI
- **WebhookEvent**: audit trail of GitHub events

---

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

---

## Dockerfile Auto-Generation

When no Dockerfile exists:
1. Detect Python version from `.python-version`, `runtime.txt`, or `pyproject.toml`
2. Install common system deps: `gcc`, `libpq-dev`, `build-essential`
3. Install Python dependencies via `pip` or `poetry`
4. Run `collectstatic --noinput` (gracefully)
5. Detect WSGI/ASGI entrypoint
6. Default CMD: `gunicorn` with configurable workers

---

## Domain + TLS Flow

1. Admin enters `app.example.com`
2. Panel shows DNS record (A/CNAME) with copy button
3. Background task polls DNS until verified
4. Caddy Admin API registers the route
5. Let's Encrypt certificate auto-provisioned on first request
6. TLS status reflected in GUI

---

## Security

- All secrets encrypted at rest using Fernet (custom EncryptedTextField)
- GitHub webhook HMAC signature verification
- Build containers have no access to host Docker socket
- DRF permissions + rate limiting on all endpoints
- Resource limits (CPU/memory) on every user container
- Django auth with token auth for API

---

## Uninstall

```bash
cd /opt/deploydjango
sudo ./uninstall.sh
```

This stops all containers and optionally wipes volumes (including your projects' data).

---

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

---

## License

MIT
