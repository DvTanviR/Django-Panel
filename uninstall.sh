#!/bin/bash
set -e

echo "=========================================="
echo "DeployDjango Platform Uninstaller"
echo "=========================================="
echo ""

INSTALL_DIR="/opt/deploydjango"
cd "$INSTALL_DIR"

echo "This will stop and remove all platform containers."
read -p "Preserve user app data and volumes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Preserving volumes..."
    docker compose -f docker/docker-compose.platform.yml down
else
    echo "Removing volumes including user data..."
    docker compose -f docker/docker-compose.platform.yml down -v
fi

echo ""
read -p "Remove $INSTALL_DIR completely? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    rm -rf "$INSTALL_DIR"
    echo "Removed $INSTALL_DIR"
fi

echo "Uninstall complete."
