# Bible Teacher - Deployment Files

This directory contains deployment configuration templates and documentation for installing the Bible Teacher application on a Linux server.

## Contents

### Documentation
- **`../MANUAL_INSTALLATION.md`** - Complete step-by-step manual installation guide
- **`QUICK_REFERENCE.md`** - Quick reference for common deployment tasks

### Configuration Files
- **`../install.config.example`** - Installation script configuration template
- **`templates/nginx.conf.template`** - Nginx web server configuration
- **`templates/gunicorn_conf.py.template`** - Gunicorn WSGI server configuration
- **`templates/bibleteacher.service.template`** - Systemd service file
- **`templates/bibleteacher.socket.template`** - Systemd socket file

## Installation Methods

### Method 1: Automated Installation (Recommended)

1. **Copy and configure the installation config:**
   ```bash
   cp install.config.example install.config
   nano install.config
   ```

2. **Edit the config file** and set:
   - Database password
   - Domain name (optional)
   - SSL settings
   - Other preferences

3. **Run the installation script:**
   ```bash
   sudo bash install.sh
   ```

### Method 2: Manual Installation

Follow the comprehensive guide in `../MANUAL_INSTALLATION.md` for step-by-step instructions.

## Template Files Usage

All template files in the `templates/` directory contain placeholders in the format `{{PLACEHOLDER}}`. 

### Common Placeholders

| Placeholder | Description | Example |
|------------|-------------|---------|
| `{{APP_NAME}}` | Application name | `bibleteacher` |
| `{{APP_DIR}}` | Application directory | `/opt/bibleteacher` |
| `{{APP_USER}}` | Application user | `bibleteacher` |
| `{{APP_GROUP}}` | Application group | `bibleteacher` |
| `{{DOMAIN}}` | Domain name | `bible.example.com` |
| `{{GUNICORN_SOCK}}` | Gunicorn socket path | `/run/gunicorn.sock` |
| `{{VENV_DIR}}` | Virtual environment path | `/opt/bibleteacher/venv` |
| `{{WORKERS}}` | Number of Gunicorn workers | `3` |

### Using Templates Manually

1. **Copy the template to the target location:**
   ```bash
   sudo cp templates/nginx.conf.template /etc/nginx/sites-available/bibleteacher
   ```

2. **Replace placeholders with actual values:**
   ```bash
   sudo sed -i 's|{{APP_DIR}}|/opt/bibleteacher|g' /etc/nginx/sites-available/bibleteacher
   sudo sed -i 's|{{DOMAIN}}|bible.example.com|g' /etc/nginx/sites-available/bibleteacher
   sudo sed -i 's|{{GUNICORN_SOCK}}|/run/gunicorn.sock|g' /etc/nginx/sites-available/bibleteacher
   ```

   Or edit manually:
   ```bash
   sudo nano /etc/nginx/sites-available/bibleteacher
   ```

3. **Enable and test the configuration:**
   ```bash
   sudo ln -s /etc/nginx/sites-available/bibleteacher /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Directory Structure After Installation

```
/opt/bibleteacher/
├── bibleteacher/           # Django project directory
│   ├── settings.py        # Django settings
│   ├── urls.py            # URL configuration
│   └── wsgi.py            # WSGI application
├── reader/                # Django app
├── media/                 # User-uploaded files
│   ├── sermons/          # Sermon audio files
│   └── sermon_notes/     # Sermon notes PDFs
├── staticfiles/          # Collected static files
├── logs/                 # Application logs
│   ├── django.log
│   ├── gunicorn_access.log
│   └── gunicorn_error.log
├── venv/                 # Python virtual environment
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
└── gunicorn_conf.py      # Gunicorn configuration
```

## System Files Locations

```
/etc/nginx/
├── sites-available/
│   └── bibleteacher              # Nginx config
└── sites-enabled/
    └── bibleteacher -> ../sites-available/bibleteacher

/etc/systemd/system/
├── bibleteacher.service          # Systemd service
└── bibleteacher.socket           # Systemd socket

/run/
└── gunicorn.sock                 # Gunicorn socket (created at runtime)

/var/log/nginx/
├── access.log                    # Nginx access log
└── error.log                     # Nginx error log
```

## Post-Installation

### Create Django Superuser

```bash
sudo -u bibleteacher /opt/bibleteacher/venv/bin/python /opt/bibleteacher/manage.py createsuperuser
```

### Access the Application

- **Main site:** `http://your-domain.com/` or `http://your-server-ip/`
- **Admin panel:** `http://your-domain.com/admin/`

### Verify Services

```bash
# Check Gunicorn
sudo systemctl status bibleteacher.service

# Check Nginx
sudo systemctl status nginx

# Check PostgreSQL
sudo systemctl status postgresql
```

## Troubleshooting

### View Logs

```bash
# Application logs
sudo tail -f /opt/bibleteacher/logs/django.log
sudo tail -f /opt/bibleteacher/logs/gunicorn_error.log

# Service logs
sudo journalctl -u bibleteacher.service -f

# Nginx logs
sudo tail -f /var/log/nginx/error.log
```

### Restart Services

```bash
# Restart application
sudo systemctl restart bibleteacher.service

# Reload Nginx (no downtime)
sudo systemctl reload nginx

# Restart Nginx
sudo systemctl restart nginx
```

### Common Issues

See the **Troubleshooting** section in `../MANUAL_INSTALLATION.md` for detailed solutions.

## Security Checklist

- [ ] Changed default database password
- [ ] Generated new Django SECRET_KEY
- [ ] Set DEBUG = False in settings.py
- [ ] Configured ALLOWED_HOSTS correctly
- [ ] Enabled UFW firewall
- [ ] Set up SSL/TLS with Let's Encrypt
- [ ] Configured fail2ban
- [ ] Set up regular database backups
- [ ] Reviewed file permissions
- [ ] Disabled SSH password authentication (use keys)

## Maintenance

### Update Application

```bash
cd /opt/bibleteacher
sudo systemctl stop bibleteacher.service
sudo -u bibleteacher git pull  # or copy new files
sudo -u bibleteacher venv/bin/pip install -r requirements.txt
sudo -u bibleteacher venv/bin/python manage.py migrate
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput
sudo systemctl start bibleteacher.service
```

### Database Backup

```bash
# Create backup
sudo -u postgres pg_dump bibleteacher > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
sudo -u postgres psql bibleteacher < backup_file.sql
```

## Support

For detailed installation instructions, see `../MANUAL_INSTALLATION.md`.

For quick reference commands, see `QUICK_REFERENCE.md`.
