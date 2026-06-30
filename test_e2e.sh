#!/bin/bash
set -e

echo "=========================================="
echo "DeployDjango End-to-End Test"
echo "=========================================="
echo ""

PANEL_DIR="/opt/deploydjango"
cd "$PANEL_DIR"

echo "1. Starting platform services..."
docker compose -f docker/docker-compose.platform.yml up -d

echo "2. Waiting for services to be healthy..."
sleep 10

echo "3. Running migrations..."
docker compose -f docker/docker-compose.platform.yml exec django python manage.py migrate

echo "4. Creating admin user..."
docker compose -f docker/docker-compose.platform.yml exec django python manage.py panel_app createadmin --username admin --password admin123 --email admin@example.com

echo ""
echo "=========================================="
echo "Test deployment with sample Django app"
echo "=========================================="
echo ""
echo "Running Phase 1 pipeline for sample app..."
python3 scripts/deploy_phase1.py testsample https://github.com/django-admin/django-admin.git main testsample.localhost

echo ""
echo "=========================================="
echo "E2E Test Complete"
echo "=========================================="
echo ""
echo "Panel should be running at http://localhost:8000"
echo "Login: admin / admin123"
echo ""
echo "Check logs:"
echo "  docker compose -f docker/docker-compose.platform.yml logs -f django"
echo "  docker compose -f docker/docker-compose.platform.yml logs -f celery"
echo ""
echo "Stop platform:"
echo "  docker compose -f docker/docker-compose.platform.yml down"
