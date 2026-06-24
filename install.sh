#!/bin/bash
#=============================================================================
# Bible Teacher - Production Installation Script for Linode (Ubuntu/Debian)
#=============================================================================
# This script performs a complete production installation:
#   - System packages (Python, PostgreSQL, Nginx, Git, etc.)
#   - PostgreSQL database and user
#   - Python virtual environment with all dependencies
#   - Django production settings (DEBUG=False, generated SECRET_KEY)
#   - Database migrations and static file collection
#   - Gunicorn systemd service
#   - Nginx reverse proxy with static/media file serving
#   - UFW firewall configuration
#   - Optional SSL via Let's Encrypt (certbot)
#
# Usage:
#   sudo bash install.sh
#
# To re-run or update an existing installation:
#   sudo bash install.sh --update
#=============================================================================

set -euo pipefail

#-----------------------------------------------------------------------------
# Configuration Variables (edit these or pass via environment)
#-----------------------------------------------------------------------------

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# Load from config file if it exists
CONFIG_FILE="${CONFIG_FILE:-./install.config}"
if [[ -f "$CONFIG_FILE" ]]; then
    info "Loading configuration from $CONFIG_FILE"
    source "$CONFIG_FILE"
fi

APP_NAME="${APP_NAME:-bibleteacher}"
APP_DIR="${APP_DIR:-/opt/bibleteacher}"
APP_USER="${APP_USER:-bibleteacher}"
APP_GROUP="${APP_GROUP:-bibleteacher}"

DB_NAME="${DB_NAME:-bibleteacher}"
DB_USER="${DB_USER:-bibleuser}"
DB_PASSWORD="${DB_PASSWORD:-}"  # MUST be set via config file or environment

VENV_DIR="${APP_DIR}/venv"
GUNICORN_SOCK="/run/gunicorn.sock"
GUNICORN_WORKERS=3

# These can be overridden via environment or prompted interactively
DOMAIN="${DOMAIN:-}"
SERVER_IP="${SERVER_IP:-}"
SETUP_SSL="${SETUP_SSL:-}"
ADMIN_EMAIL="${ADMIN_EMAIL:-}"

#-----------------------------------------------------------------------------
# Pre-flight Checks
#-----------------------------------------------------------------------------
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)."
    fi
}

detect_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS_ID=$ID
        OS_VERSION=$VERSION_ID
        info "Detected OS: ${PRETTY_NAME:-$OS_ID $OS_VERSION}"
    else
        error "Cannot detect OS. This script supports Ubuntu 20.04+ and Debian 11+."
    fi

    if [[ "$OS_ID" != "ubuntu" && "$OS_ID" != "debian" ]]; then
        error "Unsupported OS: $OS_ID. This script supports Ubuntu and Debian only."
    fi
}

check_python_version() {
    local py_cmd=""
    if command -v python3.12 &>/dev/null; then
        py_cmd="python3.12"
    elif command -v python3.11 &>/dev/null; then
        py_cmd="python3.11"
    elif command -v python3.10 &>/dev/null; then
        py_cmd="python3.10"
    elif command -v python3 &>/dev/null; then
        py_cmd="python3"
    fi

    if [[ -z "$py_cmd" ]]; then
        echo ""
        return
    fi

    local version=$($py_cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
    echo "$version"
}

get_server_ip() {
    if [[ -z "$SERVER_IP" ]]; then
        SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || curl -s icanhazip.com 2>/dev/null || echo "")
        if [[ -z "$SERVER_IP" ]]; then
            warn "Could not auto-detect server IP."
            read -p "Enter the server's public IP address: " SERVER_IP
        fi
    fi
    info "Server IP: $SERVER_IP"
}

collect_input() {
    echo ""
    echo "=========================================="
    echo " Bible Teacher - Installation Setup"
    echo "=========================================="
    echo ""

    # Prompt for database password if not set
    if [[ -z "$DB_PASSWORD" ]]; then
        read -sp "Enter database password for user '$DB_USER': " DB_PASSWORD
        echo ""
        read -sp "Confirm database password: " DB_PASSWORD_CONFIRM
        echo ""
        if [[ "$DB_PASSWORD" != "$DB_PASSWORD_CONFIRM" ]]; then
            error "Passwords do not match. Please run the script again."
        fi
        if [[ -z "$DB_PASSWORD" ]]; then
            error "Database password cannot be empty."
        fi
    fi

    if [[ -z "$DOMAIN" ]]; then
        read -p "Enter your domain name (e.g., bible.example.com) [leave blank to use IP only]: " DOMAIN
    fi

    get_server_ip

    if [[ -z "$SETUP_SSL" ]]; then
        if [[ -n "$DOMAIN" ]]; then
            read -p "Set up SSL with Let's Encrypt? (y/n) [y]: " SETUP_SSL
            SETUP_SSL=${SETUP_SSL:-y}
        else
            SETUP_SSL="n"
        fi
    fi

    if [[ "$SETUP_SSL" == "y" && -z "$ADMIN_EMAIL" ]]; then
        read -p "Enter admin email for Let's Encrypt notifications: " ADMIN_EMAIL
    fi

    echo ""
    info "Configuration summary:"
    info "  App directory:  $APP_DIR"
    info "  App user:       $APP_USER"
    info "  Database:       $DB_NAME (user: $DB_USER)"
    info "  Domain:         ${DOMAIN:-<none, using IP>}"
    info "  Server IP:      $SERVER_IP"
    info "  SSL:            $SETUP_SSL"
    if [[ -n "$ADMIN_EMAIL" ]]; then
        info "  Admin email:    $ADMIN_EMAIL"
    fi
    echo ""

    read -p "Proceed with installation? (y/n) [y]: " CONFIRM
    CONFIRM=${CONFIRM:-y}
    if [[ "$CONFIRM" != "y" ]]; then
        info "Installation cancelled."
        exit 0
    fi
}

#-----------------------------------------------------------------------------
# Step 1: Install System Packages
#-----------------------------------------------------------------------------
install_system_packages() {
    info "Step 1: Installing system packages..."

    export DEBIAN_FRONTEND=noninteractive

    apt-get update -qq
    apt-get upgrade -y -qq

    apt-get install -y -qq \
        python3 \
        python3-venv \
        python3-dev \
        python3-pip \
        postgresql \
        postgresql-contrib \
        libpq-dev \
        nginx \
        curl \
        git \
        build-essential \
        libffi-dev \
        libssl-dev \
        pkg-config \
        ufw \
        fail2ban \
        >/dev/null 2>&1

    # Install certbot for SSL if requested
    if [[ "$SETUP_SSL" == "y" ]]; then
        apt-get install -y -qq certbot python3-certbot-nginx >/dev/null 2>&1
    fi

    ok "System packages installed."
}

#-----------------------------------------------------------------------------
# Step 2: Create Application User
#-----------------------------------------------------------------------------
create_app_user() {
    info "Step 2: Creating application user..."

    if id "$APP_USER" &>/dev/null; then
        info "User '$APP_USER' already exists."
    else
        useradd --system --no-create-home --shell /bin/bash --group "$APP_GROUP" "$APP_USER"
        ok "Created system user: $APP_USER"
    fi
}

#-----------------------------------------------------------------------------
# Step 3: Set Up Application Directory
#-----------------------------------------------------------------------------
setup_app_directory() {
    info "Step 3: Setting up application directory..."

    # If app dir doesn't exist, create it and copy current project
    if [[ ! -d "$APP_DIR" ]]; then
        mkdir -p "$APP_DIR"

        # Copy the project files (excluding venv, __pycache__, media, staticfiles)
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [[ -f "$SCRIPT_DIR/manage.py" ]]; then
            info "Copying project files from $SCRIPT_DIR to $APP_DIR..."
            rsync -a --exclude='venv' --exclude='__pycache__' \
                     --exclude='media' --exclude='staticfiles' \
                     --exclude='.git' --exclude='*.pyc' \
                     "$SCRIPT_DIR/" "$APP_DIR/"
            ok "Project files copied."
        else
            warn "Could not find project files relative to script."
            warn "If you cloned this repo elsewhere, manually copy files to $APP_DIR"
            warn "and re-run this script with --update"
            # Create minimal structure
            mkdir -p "$APP_DIR"
        fi
    else
        info "App directory already exists at $APP_DIR"
        # Update files if running from script location
        SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
        if [[ -f "$SCRIPT_DIR/manage.py" && "$SCRIPT_DIR" != "$APP_DIR" ]]; then
            info "Updating project files from $SCRIPT_DIR..."
            rsync -a --exclude='venv' --exclude='__pycache__' \
                     --exclude='media' --exclude='staticfiles' \
                     --exclude='.git' --exclude='*.pyc' \
                     --exclude='bibleteacher/settings.py' \
                     "$SCRIPT_DIR/" "$APP_DIR/"
            ok "Project files updated (settings.py preserved)."
        fi
    fi

    # Create media and staticfiles directories
    mkdir -p "$APP_DIR/media/sermons"
    mkdir -p "$APP_DIR/media/sermon_notes"
    mkdir -p "$APP_DIR/staticfiles"

    # Set ownership
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR"

    ok "Application directory ready at $APP_DIR"
}

#-----------------------------------------------------------------------------
# Step 4: Configure PostgreSQL
#-----------------------------------------------------------------------------
setup_postgresql() {
    info "Step 4: Configuring PostgreSQL..."

    # Ensure PostgreSQL is running
    systemctl start postgresql
    systemctl enable postgresql >/dev/null 2>&1

    # Check if database already exists
    local db_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='$DB_NAME'" 2>/dev/null || echo "")
    if [[ "$db_exists" == "1" ]]; then
        info "Database '$DB_NAME' already exists."
    else
        sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" >/dev/null 2>&1
        ok "Created database: $DB_NAME"
    fi

    # Check if user already exists
    local user_exists=$(sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER'" 2>/dev/null || echo "")
    if [[ "$user_exists" == "1" ]]; then
        info "Database user '$DB_USER' already exists."
        # Ensure password is set correctly
        sudo -u postgres psql -c "ALTER USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" >/dev/null 2>&1
    else
        sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" >/dev/null 2>&1
        ok "Created database user: $DB_USER"
    fi

    # Grant privileges
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" >/dev/null 2>&1
    sudo -u postgres psql -d "$DB_NAME" -c "GRANT ALL ON SCHEMA public TO $DB_USER;" >/dev/null 2>&1

    ok "PostgreSQL configured."
}

#-----------------------------------------------------------------------------
# Step 5: Set Up Python Virtual Environment
#-----------------------------------------------------------------------------
setup_python_env() {
    info "Step 5: Setting up Python virtual environment..."

    # Detect best available Python version
    local py_bin="python3"
    for ver in 3.12 3.11 3.10; do
        if command -v "python$ver" &>/dev/null; then
            py_bin="python$ver"
            break
        fi
    done
    info "Using Python: $($py_bin --version)"

    # Create venv if it doesn't exist
    if [[ ! -d "$VENV_DIR" ]]; then
        sudo -u "$APP_USER" "$py_bin" -m venv "$VENV_DIR"
        ok "Virtual environment created at $VENV_DIR"
    else
        info "Virtual environment already exists."
    fi

    # Upgrade pip
    sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel -q

    # Install requirements
    if [[ -f "$APP_DIR/requirements.txt" ]]; then
        info "Installing Python dependencies..."
        sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt" -q
        ok "Python dependencies installed."
    else
        warn "requirements.txt not found. Installing core packages individually..."
        sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install \
            "Django==6.0.6" \
            "psycopg2-binary>=2.9.9" \
            "python-docx>=1.1.0" \
            "requests>=2.31.0" \
            "beautifulsoup4>=4.12.0" \
            "lxml>=5.0.0" \
            "Pillow>=10.0.0" \
            "mutagen>=1.47.0" \
            "gunicorn>=21.2.0" \
            -q
        ok "Core Python packages installed."
    fi

    # Install gunicorn (ensure it's there even if not in requirements.txt)
    sudo -u "$APP_USER" "$VENV_DIR/bin/pip" install "gunicorn>=21.2.0" -q 2>/dev/null || true

    ok "Python environment ready."
}

#-----------------------------------------------------------------------------
# Step 6: Configure Django Production Settings
#-----------------------------------------------------------------------------
generate_secret_key() {
    "$VENV_DIR/bin/python" -c "
import secrets
chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
print(''.join(secrets.choice(chars) for _ in range(50)))
"
}

configure_django_settings() {
    info "Step 6: Configuring Django production settings..."

    local settings_file="$APP_DIR/bibleteacher/settings.py"

    if [[ ! -f "$settings_file" ]]; then
        error "settings.py not found at $settings_file"
    fi

    # Back up original settings
    cp "$settings_file" "${settings_file}.bak.$(date +%Y%m%d%H%M%S)"

    # Generate a new SECRET_KEY
    local new_secret_key=$(generate_secret_key)

    # Build ALLOWED_HOSTS list
    local allowed_hosts="'localhost', '127.0.0.1', '$SERVER_IP'"
    if [[ -n "$DOMAIN" ]]; then
        allowed_hosts="'$DOMAIN', 'www.$DOMAIN', $allowed_hosts"
    fi

    # Apply settings changes with Python (more reliable than sed for complex replacements)
    "$VENV_DIR/bin/python" - <<'PYEOF'
import re
import sys

settings_path = sys.argv[1] if len(sys.argv) > 1 else "/opt/bibleteacher/bibleteacher/settings.py"
secret_key = sys.argv[2] if len(sys.argv) > 2 else ""
allowed_hosts = sys.argv[3] if len(sys.argv) > 3 else ""

with open(settings_path, 'r') as f:
    content = f.read()

# Replace SECRET_KEY
content = re.sub(
    r"SECRET_KEY\s*=\s*['\"][^'\"]*['\"]",
    f"SECRET_KEY = '{secret_key}'",
    content
)

# Replace DEBUG = True with DEBUG = False
content = re.sub(
    r"DEBUG\s*=\s*True",
    "DEBUG = False",
    content
)

# Replace ALLOWED_HOSTS
content = re.sub(
    r"ALLOWED_HOSTS\s*=\s*\[[^\]]*\]",
    f"ALLOWED_HOSTS = [{allowed_hosts}]",
    content
)

# Add production security settings at the end if not already present
if 'SECURE_PROXY_SSL_HEADER' not in content:
    content += """

# Production security settings
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Logging
import os
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s %(name)s: %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'maxBytes': 10485760,
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
"""

with open(settings_path, 'w') as f:
    f.write(content)

print("Settings updated successfully.")
PYEOF
    "$VENV_DIR/bin/python" - "$settings_file" "$new_secret_key" "$allowed_hosts"

    # Create logs directory
    mkdir -p "$APP_DIR/logs"
    touch "$APP_DIR/logs/django.log"
    chown -R "$APP_USER:$APP_GROUP" "$APP_DIR/logs"

    ok "Django production settings configured."
    info "  - DEBUG = False"
    info "  - New SECRET_KEY generated"
    info "  - ALLOWED_HOSTS = [$allowed_hosts]"
    info "  - Security headers added"
    info "  - Logging configured to $APP_DIR/logs/django.log"
}

#-----------------------------------------------------------------------------
# Step 7: Run Migrations and Collect Static Files
#-----------------------------------------------------------------------------
run_django_setup() {
    info "Step 7: Running Django migrations and collecting static files..."

    cd "$APP_DIR"

    # Create cache table (used by DatabaseCache)
    info "  Creating cache table..."
    sudo -u "$APP_USER" "$VENV_DIR/bin/python" manage.py createcachetable bible_cache_table 2>&1 || true

    # Run migrations
    info "  Running migrations..."
    sudo -u "$APP_USER" "$VENV_DIR/bin/python" manage.py migrate --noinput 2>&1

    # Collect static files
    info "  Collecting static files..."
    sudo -u "$APP_USER" "$VENV_DIR/bin/python" manage.py collectstatic --noinput 2>&1

    # Check Django deployment
    info "  Running Django system check..."
    sudo -u "$APP_USER" "$VENV_DIR/bin/python" manage.py check --deploy 2>&1 || true

    ok "Django setup complete."
}

#-----------------------------------------------------------------------------
# Step 8: Configure Gunicorn Systemd Service
#-----------------------------------------------------------------------------
setup_gunicorn() {
    info "Step 8: Configuring Gunicorn systemd service..."

    # Create gunicorn config file in the app directory
    cat > "$APP_DIR/gunicorn_conf.py" <<GUNICORN_CONF
import multiprocessing

bind = 'unix:${GUNICORN_SOCK}'
workers = ${GUNICORN_WORKERS}
worker_class = 'sync'
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
loglevel = 'info'
accesslog = '${APP_DIR}/logs/gunicorn_access.log'
errorlog = '${APP_DIR}/logs/gunicorn_error.log'
proc_name = '${APP_NAME}'
GUNICORN_CONF

    chown "$APP_USER:$APP_GROUP" "$APP_DIR/gunicorn_conf.py"

    # Create systemd socket file
    cat > /etc/systemd/system/${APP_NAME}.socket <<SOCKET_FILE
[Unit]
Description=Gunicorn socket for ${APP_NAME}

[Socket]
ListenStream=${GUNICORN_SOCK}
SocketUser=${APP_USER}
SocketGroup=www-data
SocketMode=0660

[Install]
WantedBy=sockets.target
SOCKET_FILE

    # Create systemd service file
    cat > /etc/systemd/system/${APP_NAME}.service <<SERVICE_FILE
[Unit]
Description=Gunicorn daemon for ${APP_NAME}
Requires=${APP_NAME}.socket
After=network.target postgresql.service

[Service]
Type=notify
User=${APP_USER}
Group=${APP_GROUP}
WorkingDirectory=${APP_DIR}
ExecStart=${VENV_DIR}/bin/gunicorn \\
          --config ${APP_DIR}/gunicorn_conf.py \\
          ${APP_NAME}.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_FILE

    # Reload systemd and enable services
    systemctl daemon-reload
    systemctl enable ${APP_NAME}.socket >/dev/null 2>&1
    systemctl enable ${APP_NAME}.service >/dev/null 2>&1

    # Start socket first, then service
    systemctl start ${APP_NAME}.socket
    systemctl restart ${APP_NAME}.service

    # Add www-data to app group so nginx can access the socket
    usermod -aG "$APP_GROUP" www-data

    ok "Gunicorn service configured and started."
}

#-----------------------------------------------------------------------------
# Step 9: Configure Nginx
#-----------------------------------------------------------------------------
setup_nginx() {
    info "Step 9: Configuring Nginx..."

    local server_name="_"
    if [[ -n "$DOMAIN" ]]; then
        server_name="$DOMAIN www.$DOMAIN"
    fi

    # Remove default site if present
    rm -f /etc/nginx/sites-enabled/default

    # Create Nginx config
    cat > /etc/nginx/sites-available/${APP_NAME} <<NGINX_CONF
server {
    listen 80;
    listen [::]:80;
    server_name ${server_name};

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Max upload size (for sermon audio and PDF files)
    client_max_body_size 100M;

    # Static files
    location /static/ {
        alias ${APP_DIR}/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files - served through Django for Range request support
    location /media/ {
        proxy_pass http://unix:${GUNICORN_SOCK};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        # Support large file downloads and Range requests
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
    }

    # Main application
    location / {
        proxy_pass http://unix:${GUNICORN_SOCK};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        # WebSocket support (for future use)
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Deny access to sensitive files
    location ~ /(\.git|\.env|settings\.py|manage\.py|requirements\.txt) {
        deny all;
        return 404;
    }

    # Error pages
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
    }
}
NGINX_CONF

    # Enable the site
    ln -sf /etc/nginx/sites-available/${APP_NAME} /etc/nginx/sites-enabled/${APP_NAME}

    # Test nginx config
    nginx -t 2>&1

    # Restart nginx
    systemctl restart nginx
    systemctl enable nginx >/dev/null 2>&1

    ok "Nginx configured and restarted."
}

#-----------------------------------------------------------------------------
# Step 10: Configure Firewall (UFW)
#-----------------------------------------------------------------------------
setup_firewall() {
    info "Step 10: Configuring firewall (UFW)..."

    # Allow SSH, HTTP, HTTPS
    ufw allow OpenSSH 2>/dev/null || ufw allow 22/tcp 2>/dev/null || true
    ufw allow 'Nginx Full' 2>/dev/null || { ufw allow 80/tcp 2>/dev/null || true; ufw allow 443/tcp 2>/dev/null || true; }

    # Enable UFW (non-interactive)
    echo "y" | ufw enable 2>/dev/null || true

    ok "Firewall configured."
    ufw status verbose 2>/dev/null || true
}

#-----------------------------------------------------------------------------
# Step 11: Set Up SSL with Let's Encrypt (Optional)
#-----------------------------------------------------------------------------
setup_ssl() {
    if [[ "$SETUP_SSL" != "y" ]]; then
        info "Step 11: SSL setup skipped."
        return
    fi

    if [[ -z "$DOMAIN" ]]; then
        warn "No domain specified - skipping SSL setup."
        return
    fi

    info "Step 11: Setting up SSL with Let's Encrypt..."

    # Wait for nginx to be ready
    sleep 2

    # Obtain SSL certificate
    certbot --nginx \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --non-interactive \
        --agree-tos \
        --email "$ADMIN_EMAIL" \
        --redirect \
        2>&1 || warn "Certbot certificate acquisition failed. You can retry manually with: sudo certbot --nginx -d $DOMAIN -d www.$DOMAIN"

    # Set up auto-renewal timer
    systemctl enable certbot.timer >/dev/null 2>&1
    systemctl start certbot.timer >/dev/null 2>&1

    ok "SSL configured (if certbot succeeded above)."
}

#-----------------------------------------------------------------------------
# Step 12: Create Superuser Prompt
#-----------------------------------------------------------------------------
prompt_superuser() {
    info "Step 12: Django superuser setup..."

    echo ""
    read -p "Create a Django superuser now? (y/n) [y]: " CREATE_SU
    CREATE_SU=${CREATE_SU:-y}

    if [[ "$CREATE_SU" == "y" ]]; then
        cd "$APP_DIR"
        sudo -u "$APP_USER" "$VENV_DIR/bin/python" manage.py createsuperuser
        ok "Superuser created."
    else
        info "You can create a superuser later with:"
        info "  sudo -u $APP_USER $VENV_DIR/bin/python $APP_DIR/manage.py createsuperuser"
    fi
}

#-----------------------------------------------------------------------------
# Final Summary
#-----------------------------------------------------------------------------
print_summary() {
    local protocol="http"
    if [[ "$SETUP_SSL" == "y" && -n "$DOMAIN" ]]; then
        protocol="https"
    fi

    local base_url="${protocol}://${DOMAIN:-$SERVER_IP}"

    echo ""
    echo "=========================================="
    echo " Installation Complete!"
    echo "=========================================="
    echo ""
    echo "  Application:   Bible Teacher"
    echo "  App directory: $APP_DIR"
    echo "  App user:      $APP_USER"
    echo "  Database:      $DB_NAME (user: $DB_USER)"
    echo "  Venv:          $VENV_DIR"
    echo ""
    echo "  URLs:"
    echo "    Main site:   $base_url/"
    echo "    Admin:       $base_url/admin/"
    echo "    Sermons:     $base_url/sermons/"
    echo "    Notes:       $base_url/notes/"
    echo ""
    echo "  Services:"
    echo "    Gunicorn:    sudo systemctl {start|stop|restart|status} ${APP_NAME}"
    echo "    Nginx:       sudo systemctl {start|stop|restart|status} nginx"
    echo "    PostgreSQL:  sudo systemctl {start|stop|restart|status} postgresql"
    echo ""
    echo "  Logs:"
    echo "    Django:      $APP_DIR/logs/django.log"
    echo "    Gunicorn:    $APP_DIR/logs/gunicorn_error.log"
    echo "    Nginx:       /var/log/nginx/error.log"
    echo ""
    echo "  Useful commands:"
    echo "    Check status:  sudo systemctl status ${APP_NAME}"
    echo "    View logs:     sudo journalctl -u ${APP_NAME} -f"
    echo "    Restart app:   sudo systemctl restart ${APP_NAME}"
    echo "    Reload nginx:  sudo systemctl reload nginx"
    echo ""
    if [[ "$SETUP_SSL" != "y" ]]; then
        echo "  To add SSL later:"
        echo "    sudo apt install certbot python3-certbot-nginx"
        echo "    sudo certbot --nginx -d ${DOMAIN:-your-domain}"
        echo ""
    fi
    echo "=========================================="
}

#-----------------------------------------------------------------------------
# Main
#-----------------------------------------------------------------------------
main() {
    echo ""
    echo "=========================================="
    echo " Bible Teacher - Production Installation"
    echo " for Linode (Ubuntu/Debian)"
    echo "=========================================="

    check_root
    detect_os

    # Handle --update flag (skip system packages and PostgreSQL)
    local update_mode=false
    if [[ "${1:-}" == "--update" ]]; then
        update_mode=true
        info "Running in UPDATE mode (skipping system packages and DB setup)."
    fi

    collect_input

    if [[ "$update_mode" == "false" ]]; then
        install_system_packages
        create_app_user
        setup_app_directory
        setup_postgresql
    else
        setup_app_directory
    fi

    setup_python_env
    configure_django_settings
    run_django_setup
    setup_gunicorn
    setup_nginx
    setup_firewall
    setup_ssl
    prompt_superuser
    print_summary
}

main "$@"
