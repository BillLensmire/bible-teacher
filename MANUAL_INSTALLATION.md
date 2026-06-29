## Bible Teacher - Manual Installation Guide

This guide provides step-by-step instructions for manually installing the Bible Teacher application on a Linux server (Ubuntu 20.04+ or Debian 11+).

## Table of Contents

1.  [Prerequisites](#prerequisites)
2.  [System Preparation](#system-preparation)
3.  [Database Setup](#database-setup)
4.  [Application Setup](#application-setup)
5.  [Web Server Configuration](#web-server-configuration)
6.  [SSL/TLS Setup](#ssltls-setup)
7.  [Troubleshooting](#troubleshooting)
8.  [Maintenance](#maintenance)

## Prerequisites

*   Fresh Ubuntu 20.04+ or Debian 11+ server
*   Root or sudo access
*   Domain name (optional, but recommended for SSL)
*   At least 1GB RAM and 10GB disk space

## System Preparation

### 1\. Update System Packages

```plaintext
sudo apt update
sudo apt upgrade -y
```

### 2\. Install Required System Packages

```plaintext
sudo apt install -y \
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
    fail2ban
```

### 3\. Create Application User

```plaintext
sudo useradd --system --no-create-home --shell /bin/bash --group bibleteacher bibleteacher
```

## Database Setup

### 1\. Start PostgreSQL Service

```plaintext
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2\. Create Database and User

```plaintext
sudo -u postgres psql
```

In the PostgreSQL prompt:

```plaintext
CREATE DATABASE bibleteacher;
CREATE USER bibleuser WITH PASSWORD 'Buck30488';
GRANT ALL PRIVILEGES ON DATABASE bibleteacher TO bibleuser;
\c bibleteacher
GRANT ALL ON SCHEMA public TO bibleuser;
\q
```

**Important:** Replace `YOUR_SECURE_PASSWORD_HERE` with a strong password. Save this password securely.

## Application Setup

### 1\. Create Application Directory

```plaintext
sudo mkdir -p /var/www/bibleteacher
cd /var/www/bibleteacher
```

### 2\. Copy Application Files

If you have the application files on your local machine, upload them:

```plaintext
# From your local machine
scp -r /path/to/bible-teacher/* user@your-server:/tmp/bibleteacher/

# On the server
sudo rsync -a --exclude='venv' --exclude='__pycache__' \
           --exclude='media' --exclude='staticfiles' \
           --exclude='.git' --exclude='*.pyc' \
           /tmp/bibleteacher/ /var/www/bibleteacher/
```

Or clone from Git repository:

```plaintext
sudo git clone https://github.com/BillLensmire/bible-teacher.git /var/www/bibleteacher
```

### 3\. Create Required Directories

```plaintext
sudo mkdir -p /var/www/bibleteacher/media/sermons
sudo mkdir -p /var/www/bibleteacher/media/sermon_notes
sudo mkdir -p /var/www/bibleteacher/staticfiles
sudo mkdir -p /var/www/bibleteacher/logs
```

### 4\. Set Up Python Virtual Environment

```plaintext
cd /var/www/bibleteacher
sudo -u bibleteacher python3 -m venv venv
sudo -u bibleteacher venv/bin/pip install --upgrade pip setuptools wheel
```

### 5\. Install Python Dependencies

```plaintext
sudo -u bibleteacher venv/bin/pip install -r requirements.txt
```

If `requirements.txt` is missing, install manually:

```plaintext
sudo -u bibleteacher venv/bin/pip install \
    Django==6.0.6 \
    psycopg2-binary \
    python-docx \
    requests \
    beautifulsoup4 \
    lxml \
    Pillow \
    mutagen \
    gunicorn
```

### 6\. Configure Django Settings

Edit the settings file:

```plaintext
sudo nano /var/www/bibleteacher/bibleteacher/settings.py
```

Update the following settings:

```python
# Generate a new SECRET_KEY (use: python3 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
SECRET_KEY = 'your-generated-secret-key-here'

# Set DEBUG to False for production
DEBUG = False

# Add your domain and server IP
ALLOWED_HOSTS = ['your-domain.com', 'www.your-domain.com', 'your-server-ip', 'localhost']

# Database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'bibleteacher',
        'USER': 'bibleuser',
        'PASSWORD': 'YOUR_SECURE_PASSWORD_HERE',  # Same as PostgreSQL password
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Static and media files
STATIC_ROOT = '/var/www/bibleteacher/staticfiles'
MEDIA_ROOT = '/var/www/bibleteacher/media'

# Security settings (add at the end of the file)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = True  # Only if using HTTPS
CSRF_COOKIE_SECURE = True     # Only if using HTTPS
```

### 7\. Run Django Migrations

```plaintext
cd /var/www/bibleteacher
sudo -u bibleteacher venv/bin/python manage.py migrate
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput
sudo -u bibleteacher venv/bin/python manage.py createcachetable bible_cache_table
```

### 8\. Create Django Superuser

```plaintext
sudo -u bibleteacher venv/bin/python manage.py createsuperuser
```

### 9\. Set Correct Permissions

```plaintext
sudo chown -R bibleteacher:bibleteacher /var/www/bibleteacher
sudo chmod -R 755 /var/www/bibleteacher
sudo chmod -R 775 /var/www/bibleteacher/media
sudo chmod -R 775 /var/www/bibleteacher/logs
```

## Web Server Configuration

### 1\. Create Gunicorn Configuration

Create `/var/www/bibleteacher/gunicorn_conf.py`:

```plaintext
sudo nano /var/www/bibleteacher/gunicorn_conf.py
```

Add the following content:

```python
import multiprocessing

bind = 'unix:/run/gunicorn.sock'
workers = 3
worker_class = 'sync'
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
loglevel = 'info'
accesslog = '/var/www/bibleteacher/logs/gunicorn_access.log'
errorlog = '/var/www/bibleteacher/logs/gunicorn_error.log'
proc_name = 'bibleteacher'
```

Set ownership:

```plaintext
sudo chown bibleteacher:bibleteacher /var/www/bibleteacher/gunicorn_conf.py
```

### 2\. Create Systemd Socket File

Create `/etc/systemd/system/bibleteacher.socket`:

```plaintext
sudo nano /etc/systemd/system/bibleteacher.socket
```

Add:

```plaintext
[Unit]
Description=Gunicorn socket for bibleteacher

[Socket]
ListenStream=/run/gunicorn.sock
SocketUser=bibleteacher
SocketGroup=www-data
SocketMode=0660

[Install]
WantedBy=sockets.target
```

### 3\. Create Systemd Service File

Create `/etc/systemd/system/bibleteacher.service`:

```plaintext
sudo nano /etc/systemd/system/bibleteacher.service
```

Add:

```plaintext
[Unit]
Description=Gunicorn daemon for bibleteacher
Requires=bibleteacher.socket
After=network.target postgresql.service

[Service]
Type=notify
User=bibleteacher
Group=bibleteacher
WorkingDirectory=/var/www/bibleteacher
ExecStart=/var/www/bibleteacher/venv/bin/gunicorn \
          --config /var/www/bibleteacher/gunicorn_conf.py \
          bibleteacher.wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 4\. Enable and Start Gunicorn

```plaintext
sudo systemctl daemon-reload
sudo systemctl enable bibleteacher.socket
sudo systemctl enable bibleteacher.service
sudo systemctl start bibleteacher.socket
sudo systemctl start bibleteacher.service
```

Verify it's running:

```plaintext
sudo systemctl status bibleteacher.service
```

### 5\. Configure Nginx

Create `/etc/nginx/sites-available/bibleteacher`:

```plaintext
sudo nano /etc/nginx/sites-available/bibleteacher
```

Add (replace `your-domain.com` with your actual domain or use `_` for IP-only access):

```plaintext
server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    # Security headers
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Max upload size (for sermon audio and PDF files)
    client_max_body_size 100M;

    # Static files
    location /static/ {
        alias /var/www/bibleteacher/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # Media files - served through Django for Range request support
    location /media/ {
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # Support large file downloads and Range requests
        proxy_buffering off;
        proxy_request_buffering off;
        proxy_read_timeout 300s;
    }

    # Main application
    location / {
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
        # WebSocket support (for future use)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
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
```

### 6\. Enable Nginx Site

```plaintext
# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Enable bibleteacher site
sudo ln -s /etc/nginx/sites-available/bibleteacher /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

### 7\. Add www-data to Application Group

```plaintext
sudo usermod -aG bibleteacher www-data
```

## SSL/TLS Setup

### 1\. Install Certbot

```plaintext
sudo apt install -y certbot python3-certbot-nginx
```

### 2\. Obtain SSL Certificate

```plaintext
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts and select option 2 to redirect HTTP to HTTPS.

### 3\. Enable Auto-Renewal

```plaintext
sudo systemctl enable certbot.timer
sudo systemctl start certbot.timer
```

Test renewal:

```plaintext
sudo certbot renew --dry-run
```

## Firewall Configuration

### 1\. Configure UFW

```plaintext
# Allow SSH
sudo ufw allow OpenSSH

# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Enable firewall
sudo ufw enable
```

### 2\. Verify Firewall Status

```plaintext
sudo ufw status verbose
```

## Troubleshooting

### Check Service Status

```plaintext
# Gunicorn
sudo systemctl status bibleteacher.service
sudo journalctl -u bibleteacher.service -f

# Nginx
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log

# PostgreSQL
sudo systemctl status postgresql
```

### Check Logs

```plaintext
# Application logs
sudo tail -f /var/www/bibleteacher/logs/django.log
sudo tail -f /var/www/bibleteacher/logs/gunicorn_error.log
sudo tail -f /var/www/bibleteacher/logs/gunicorn_access.log

# Nginx logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Common Issues

#### 1\. Gunicorn Socket Not Found

```plaintext
# Check socket exists
ls -l /run/gunicorn.sock

# Restart socket
sudo systemctl restart bibleteacher.socket
sudo systemctl restart bibleteacher.service
```

#### 2\. Permission Denied Errors

```plaintext
# Fix ownership
sudo chown -R bibleteacher:bibleteacher /var/www/bibleteacher
sudo chmod -R 755 /var/www/bibleteacher
sudo chmod -R 775 /var/www/bibleteacher/media
sudo chmod -R 775 /var/www/bibleteacher/logs

# Ensure www-data can access socket
sudo usermod -aG bibleteacher www-data
sudo systemctl restart nginx
```

#### 3\. Database Connection Errors

```plaintext
# Test PostgreSQL connection
sudo -u postgres psql -c "SELECT 1"

# Verify database exists
sudo -u postgres psql -l | grep bibleteacher

# Check user permissions
sudo -u postgres psql -c "\du bibleuser"
```

#### 4\. Static Files Not Loading

```plaintext
# Recollect static files
cd /var/www/bibleteacher
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput

# Check permissions
sudo chmod -R 755 /var/www/bibleteacher/staticfiles
```

## Maintenance

### Update Application Code

```plaintext
# Stop service
sudo systemctl stop bibleteacher.service

# Pull latest code (if using Git)
cd /var/www/bibleteacher
sudo -u bibleteacher git pull

# Or copy new files
sudo rsync -a --exclude='venv' --exclude='media' \
           --exclude='staticfiles' --exclude='*.pyc' \
           /path/to/new/files/ /var/www/bibleteacher/

# Update dependencies
sudo -u bibleteacher venv/bin/pip install -r requirements.txt

# Run migrations
sudo -u bibleteacher venv/bin/python manage.py migrate

# Collect static files
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput

# Restart service
sudo systemctl start bibleteacher.service
```

### Database Backup

```plaintext
# Create backup
sudo -u postgres pg_dump bibleteacher &gt; backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
sudo -u postgres psql bibleteacher &lt; backup_file.sql
```

### View Application Logs

```plaintext
# Real-time Django logs
sudo tail -f /var/www/bibleteacher/logs/django.log

# Real-time Gunicorn logs
sudo tail -f /var/www/bibleteacher/logs/gunicorn_error.log

# Service logs
sudo journalctl -u bibleteacher.service -f
```

### Restart Services

```plaintext
# Restart application
sudo systemctl restart bibleteacher.service

# Reload Nginx (without downtime)
sudo systemctl reload nginx

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## Security Recommendations

**Keep system updated:**

**Configure fail2ban:**

**Regular backups:**

*   Database backups daily
*   Media files backups weekly
*   Store backups off-server

**Monitor logs regularly:**

*   Check for unauthorized access attempts
*   Monitor application errors
*   Review Nginx access logs

**Use strong passwords:**

*   Database passwords
*   Django admin passwords
*   Server SSH keys (disable password auth)

## Support

For issues or questions:

*   Check the logs in `/var/www/bibleteacher/logs/`
*   Review Django documentation: https://docs.djangoproject.com/
*   Check Nginx documentation: https://nginx.org/en/docs/

```plaintext
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

```plaintext
sudo apt update &amp;&amp; sudo apt upgrade -y
```