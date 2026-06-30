#!/bin/bash
set -e

echo "=========================================="
echo "DeployDjango Platform Installer"
echo "=========================================="
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo bash install.sh)"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
    VERSION=$VERSION_ID
else
    echo "Cannot detect OS"
    exit 1
fi

case $OS in
    ubuntu)
        case $VERSION in
            20.04|22.04|24.04) echo "Detected Ubuntu $VERSION" ;;
            *) echo "Ubuntu $VERSION not supported. Need 20.04, 22.04, or 24.04."; exit 1 ;;
        esac
        ;;
    *) echo "OS $OS not supported. Please use Ubuntu."; exit 1 ;;
esac

# Install Docker if needed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    apt-get update
    apt-get install -y ca-certificates curl gnupg lsb-release
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
else
    echo "Docker already installed"
fi

if ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose plugin..."
    apt-get update
    apt-get install -y docker-compose-plugin
fi

mkdir -p /opt/deploydjango
INSTALL_DIR="/opt/deploydjango"

# If running from a cloned repo, copy files. Otherwise clone from GitHub.
if [ -f "django_panel/manage.py" ]; then
    echo "Copying from local repo..."
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    cp -r $SCRIPT_DIR/* $INSTALL_DIR/
elif [ -d ".git" ]; then
    echo "Copying from git repo..."
    git archive --format=tar HEAD | tar -xf - -C $INSTALL_DIR/
else
    echo "Cloning from GitHub..."
    git clone https://github.com/DvTanviR/Django-Panel.git $INSTALL_DIR
fi

cd $INSTALL_DIR

# Create .env file
if [ ! -f .env ]; then
    echo "Generating secrets..."
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
    POSTGRES_PASSWORD=$(openssl rand -base64 24)
    REDIS_PASSWORD=$(openssl rand -base64 24)
    ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    WEBHOOK_SECRET=$(openssl rand -base64 24)
    
    cat > .env << EOF
DJANGO_SECRET_KEY=$SECRET_KEY
DJANGO_DEBUG=False
POSTGRES_DB=panel
POSTGRES_USER=panel
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_HOST=db
POSTGRES_PORT=5432
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
ENCRYPTION_KEY=$ENCRYPTION_KEY
DOCKER_SOCKET=/var/run/docker.sock
DEPLOYMENTS_DIR=/app/deployments
BASE_DOMAIN=localhost
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "127.0.0.1")
CADDY_ADMIN_API=http://caddy:2019
GITHUB_WEBHOOK_SECRET=$WEBHOOK_SECRET
EOF
    chmod 600 .env
fi

# Install CLI
echo "Installing djpaas CLI..."
cp $INSTALL_DIR/scripts/djpaas /usr/local/bin/djpaas
chmod +x /usr/local/bin/djpaas

# Start platform
echo ""
echo "Starting platform services..."
docker compose -f docker/docker-compose.platform.yml up -d

echo "Waiting for services to be ready..."
sleep 15

echo "Running database migrations..."
docker compose -f docker/docker-compose.platform.yml exec django python manage.py migrate

echo "Creating admin user..."
docker compose -f docker/docker-compose.platform.yml exec django python manage.py panel_app createadmin --username admin --password admin123 --email admin@example.com

IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Panel URL:      http://$IP:8000"
echo "Admin user:     admin / admin123"
echo "CLI:            djpaas status"
echo "Config:         /opt/deploydjango/.env"
echo ""
echo "Next steps:"
echo "  1. Open http://$IP:8000 and log in"
echo "  2. Click 'New Project' to deploy your first Django app"
echo "  3. Use 'djpaas' CLI to manage projects from the command line"
echo ""
echo "To stop:   docker compose -f docker/docker-compose.platform.yml down"
echo "To remove: sudo ./uninstall.sh"
echo ""
