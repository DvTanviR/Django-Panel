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
http://YOUR-SERVER-IP:8000
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
http://<project-slug>.localhost
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
| Caddy | Reverse proxy + auto TLS | 80, 443, 2019 |
| Django | Control plane / API | 8000 |
| Celery | Async build/deploy worker | — |
| Redis | Task queue | 6379 |
| PostgreSQL | Metadata database | 5432 |

Your Django apps each run in **their own isolated container** with configurable CPU/memory limits, routed through Caddy.

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

## Uninstall

```bash
cd /opt/deploydjango
sudo ./uninstall.sh
```

This stops all containers and optionally wipes volumes (including your projects' data).

---

## Tech Stack

- **Backend**: Django + DRF (Python 3.12)
- **Database**: PostgreSQL (Dockerized)
- **Queue**: Celery + Redis (Dockerized)
- **Frontend**: Next.js 14 + Tailwind CSS
- **Proxy**: Caddy v2 (Admin API for dynamic routing + auto TLS)
- **Runtime**: Docker Engine via docker-py

---

## License

MIT
