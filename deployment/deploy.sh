#!/bin/bash
#=============================================================================
# Bible Teacher - Local Deploy Script
#=============================================================================
# Deploys the application to an Akamai (Linode) server via SSH.
# Usage: bash deployment/deploy.sh
#
# Requires: deployment/deploy.env configured with server details.
#=============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Load deploy config
DEPLOY_ENV="${PROJECT_ROOT}/deployment/deploy.env"
if [[ ! -f "$DEPLOY_ENV" ]]; then
    error "Deploy config not found: $DEPLOY_ENV"
    error "Copy deployment/deploy.env.example to deployment/deploy.env and edit it."
fi
source "$DEPLOY_ENV"

# Validate required variables
: "${DEPLOY_HOST:?DEPLOY_HOST is required in deploy.env}"
: "${DEPLOY_USER:?DEPLOY_USER is required in deploy.env}"
: "${APP_DIR:?APP_DIR is required in deploy.env}"
: "${APP_USER:?APP_USER is required in deploy.env}"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

info "Deploying to ${DEPLOY_USER}@${DEPLOY_HOST}"
info "Application directory: ${APP_DIR}"

#-------------------------------------------------------------------------
# Deploy commands run on the remote server
#-------------------------------------------------------------------------
REMOTE_CMDS=$(cat << EOF
set -e
echo "=== Starting deployment at \$(date) ==="

cd ${APP_DIR}

# Pull latest code
echo "[1/5] Pulling latest code..."
sudo -u ${APP_USER} git pull origin main

# Install/update Python dependencies
echo "[2/5] Installing dependencies..."
sudo -u ${APP_USER} ${APP_DIR}/venv/bin/pip install -r requirements.txt

# Run migrations
echo "[3/5] Running database migrations..."
sudo -u ${APP_USER} ${APP_DIR}/venv/bin/python manage.py migrate --noinput

# Collect static files
echo "[4/5] Collecting static files..."
sudo -u ${APP_USER} ${APP_DIR}/venv/bin/python manage.py collectstatic --noinput

# Restart application service
echo "[5/5] Restarting Gunicorn..."
sudo systemctl restart bibleteacher.service

echo "=== Deployment complete at \$(date) ==="
EOF
)

# Execute remote commands via SSH
if ssh ${SSH_OPTS} "${DEPLOY_USER}@${DEPLOY_HOST}" "$REMOTE_CMDS"; then
    ok "Deployment successful!"
else
    error "Deployment failed. Check the output above for errors."
fi
