# Bible Teacher - Deployment Checklist

Use this checklist to ensure a complete and secure deployment.

## Pre-Deployment

### Server Preparation
- [ ] Fresh Ubuntu 20.04+ or Debian 11+ server provisioned
- [ ] Root or sudo access confirmed
- [ ] Server has at least 1GB RAM and 10GB disk space
- [ ] Server IP address noted: `___________________`
- [ ] Domain name registered (if using): `___________________`
- [ ] DNS A record pointing to server IP (if using domain)

### Local Preparation
- [ ] Application code ready to deploy
- [ ] `requirements.txt` is up to date
- [ ] Database migrations are current
- [ ] Static files are properly configured

## Installation Configuration

### Option A: Automated Installation
- [ ] Copied `install.config.example` to `install.config`
- [ ] Set strong database password in config
- [ ] Configured domain name (or left blank for IP-only)
- [ ] Set SSL preferences
- [ ] Set admin email (if using SSL)
- [ ] Reviewed all configuration values

### Option B: Manual Installation
- [ ] Read through `MANUAL_INSTALLATION.md`
- [ ] Prepared all required values:
  - Database password: `___________________`
  - Domain name: `___________________`
  - Admin email: `___________________`

## Installation Steps

### System Setup
- [ ] Updated system packages (`apt update && apt upgrade`)
- [ ] Installed required system packages
- [ ] Created application user (`bibleteacher`)
- [ ] Created application directory (`/opt/bibleteacher`)

### Database Setup
- [ ] PostgreSQL installed and running
- [ ] Database created (`bibleteacher`)
- [ ] Database user created (`bibleuser`)
- [ ] Strong password set for database user
- [ ] Database permissions granted

### Application Setup
- [ ] Application files copied to `/opt/bibleteacher`
- [ ] Python virtual environment created
- [ ] Python dependencies installed
- [ ] Django settings configured:
  - [ ] New SECRET_KEY generated
  - [ ] DEBUG set to False
  - [ ] ALLOWED_HOSTS configured
  - [ ] Database credentials set
  - [ ] STATIC_ROOT and MEDIA_ROOT set
- [ ] Database migrations run successfully
- [ ] Static files collected
- [ ] Cache table created
- [ ] Django superuser created
- [ ] File permissions set correctly

### Web Server Setup
- [ ] Gunicorn configuration created
- [ ] Systemd socket file created
- [ ] Systemd service file created
- [ ] Services enabled and started
- [ ] Nginx installed and configured
- [ ] Nginx configuration tested (`nginx -t`)
- [ ] Nginx restarted successfully

### Security Setup
- [ ] UFW firewall enabled
- [ ] SSH access allowed in firewall
- [ ] HTTP (80) and HTTPS (443) allowed in firewall
- [ ] fail2ban installed and configured
- [ ] SSL certificate obtained (if using domain)
- [ ] SSL auto-renewal configured
- [ ] Security headers configured in Nginx

## Post-Deployment Verification

### Service Status
- [ ] Gunicorn service running: `systemctl status bibleteacher.service`
- [ ] Nginx service running: `systemctl status nginx`
- [ ] PostgreSQL service running: `systemctl status postgresql`
- [ ] No errors in service logs

### Application Access
- [ ] Main site accessible: `http://your-domain-or-ip/`
- [ ] Admin panel accessible: `http://your-domain-or-ip/admin/`
- [ ] Can log in with superuser credentials
- [ ] Static files loading correctly
- [ ] No 404 errors for CSS/JS files

### SSL/HTTPS (if configured)
- [ ] HTTPS accessible: `https://your-domain/`
- [ ] HTTP redirects to HTTPS
- [ ] SSL certificate valid
- [ ] No browser security warnings
- [ ] Certificate auto-renewal timer active

### Functionality Testing
- [ ] Can log in to admin panel
- [ ] Can create/edit/delete content
- [ ] Can upload files (sermons, notes)
- [ ] Media files are accessible
- [ ] Audio player works correctly
- [ ] PDF downloads work
- [ ] Search functionality works
- [ ] All pages load without errors

## Security Hardening

### Credentials
- [ ] Database password is strong and unique
- [ ] Django SECRET_KEY is unique and not default
- [ ] Superuser password is strong
- [ ] All passwords stored securely (password manager)

### File Permissions
- [ ] Application files owned by `bibleteacher:bibleteacher`
- [ ] Sensitive files not world-readable
- [ ] Media directory has correct permissions (775)
- [ ] Log directory has correct permissions (775)

### Django Settings
- [ ] DEBUG = False
- [ ] ALLOWED_HOSTS properly configured
- [ ] SECURE_PROXY_SSL_HEADER set (if using SSL)
- [ ] SESSION_COOKIE_SECURE = True (if using SSL)
- [ ] CSRF_COOKIE_SECURE = True (if using SSL)
- [ ] Security middleware enabled

### Server Security
- [ ] SSH password authentication disabled (using keys)
- [ ] Root login disabled
- [ ] Firewall configured and enabled
- [ ] fail2ban configured
- [ ] System packages up to date
- [ ] Unnecessary services disabled

## Backup Configuration

### Database Backups
- [ ] Backup script created
- [ ] Backup location configured: `___________________`
- [ ] Automated backup schedule set up
- [ ] Backup restoration tested
- [ ] Off-site backup configured

### File Backups
- [ ] Media files backup configured
- [ ] Backup retention policy defined
- [ ] Backup monitoring set up

## Monitoring Setup

### Log Monitoring
- [ ] Know where to find logs:
  - Django: `/opt/bibleteacher/logs/django.log`
  - Gunicorn: `/opt/bibleteacher/logs/gunicorn_error.log`
  - Nginx: `/var/log/nginx/error.log`
- [ ] Log rotation configured
- [ ] Log monitoring/alerting set up (optional)

### Uptime Monitoring
- [ ] Uptime monitoring service configured (optional)
- [ ] Alert notifications configured (optional)

## Documentation

### Internal Documentation
- [ ] Server details documented:
  - Server IP: `___________________`
  - Domain: `___________________`
  - Database password location: `___________________`
  - SSH key location: `___________________`
- [ ] Deployment date recorded: `___________________`
- [ ] Deployment performed by: `___________________`

### Team Knowledge
- [ ] Team members know how to access logs
- [ ] Team members know how to restart services
- [ ] Emergency contact information documented
- [ ] Backup restoration procedure documented

## Maintenance Planning

### Regular Tasks
- [ ] Weekly: Review logs for errors
- [ ] Weekly: Check disk space usage
- [ ] Monthly: Review security updates
- [ ] Monthly: Test backup restoration
- [ ] Quarterly: Review and update dependencies

### Update Procedure
- [ ] Update procedure documented
- [ ] Rollback procedure documented
- [ ] Maintenance window scheduled (if needed)

## Final Steps

### Cleanup
- [ ] Removed any test data
- [ ] Removed installation files from server (if sensitive)
- [ ] Cleared bash history if it contains passwords

### Handoff
- [ ] Deployment documentation provided
- [ ] Access credentials shared securely
- [ ] Support contact information provided
- [ ] Training completed (if needed)

## Sign-Off

**Deployment completed by:** `___________________`

**Date:** `___________________`

**Server IP:** `___________________`

**Domain:** `___________________`

**Notes:**
```
_______________________________________________________________________________
_______________________________________________________________________________
_______________________________________________________________________________
```

---

## Quick Reference

### Important Commands

```bash
# Restart application
sudo systemctl restart bibleteacher.service

# View application logs
sudo tail -f /opt/bibleteacher/logs/django.log

# Create database backup
sudo -u postgres pg_dump bibleteacher > backup_$(date +%Y%m%d).sql

# Update application
cd /opt/bibleteacher
sudo systemctl stop bibleteacher.service
sudo -u bibleteacher git pull
sudo -u bibleteacher venv/bin/pip install -r requirements.txt
sudo -u bibleteacher venv/bin/python manage.py migrate
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput
sudo systemctl start bibleteacher.service
```

### Important Files

- Configuration: `/opt/bibleteacher/bibleteacher/settings.py`
- Gunicorn config: `/opt/bibleteacher/gunicorn_conf.py`
- Nginx config: `/etc/nginx/sites-available/bibleteacher`
- Systemd service: `/etc/systemd/system/bibleteacher.service`
- Systemd socket: `/etc/systemd/system/bibleteacher.socket`

### Support Resources

- Manual Installation Guide: `MANUAL_INSTALLATION.md`
- Quick Reference: `QUICK_REFERENCE.md`
- Deployment README: `deployment/README.md`
