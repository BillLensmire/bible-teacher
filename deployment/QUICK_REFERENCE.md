# Bible Teacher - Quick Reference Guide

## Service Management

### Gunicorn (Application Server)

```bash
# Status
sudo systemctl status bibleteacher.service

# Start
sudo systemctl start bibleteacher.service

# Stop
sudo systemctl stop bibleteacher.service

# Restart
sudo systemctl restart bibleteacher.service

# Enable on boot
sudo systemctl enable bibleteacher.service

# View logs
sudo journalctl -u bibleteacher.service -f
```

### Nginx (Web Server)

```bash
# Status
sudo systemctl status nginx

# Start
sudo systemctl start nginx

# Stop
sudo systemctl stop nginx

# Restart (brief downtime)
sudo systemctl restart nginx

# Reload (no downtime)
sudo systemctl reload nginx

# Test configuration
sudo nginx -t

# Enable on boot
sudo systemctl enable nginx
```

### PostgreSQL (Database)

```bash
# Status
sudo systemctl status postgresql

# Start
sudo systemctl start postgresql

# Stop
sudo systemctl stop postgresql

# Restart
sudo systemctl restart postgresql

# Access database
sudo -u postgres psql bibleteacher
```

## Log Files

### View Logs

```bash
# Django application log
sudo tail -f /var/www/bibleteacher/logs/django.log

# Gunicorn access log
sudo tail -f /var/www/bibleteacher/logs/gunicorn_access.log

# Gunicorn error log
sudo tail -f /var/www/bibleteacher/logs/gunicorn_error.log

# Nginx access log
sudo tail -f /var/log/nginx/access.log

# Nginx error log
sudo tail -f /var/log/nginx/error.log

# Systemd service log
sudo journalctl -u bibleteacher.service -f

# PostgreSQL log
sudo tail -f /var/log/postgresql/postgresql-*-main.log
```

### Search Logs

```bash
# Search for errors in Django log
sudo grep -i error /var/www/bibleteacher/logs/django.log

# Last 100 lines of Gunicorn errors
sudo tail -n 100 /var/www/bibleteacher/logs/gunicorn_error.log

# Search systemd logs for specific date
sudo journalctl -u bibleteacher.service --since "2024-01-01" --until "2024-01-02"
```

## Django Management

### Common Commands

```bash
# Run as bibleteacher user
cd /var/www/bibleteacher
sudo -u bibleteacher venv/bin/python manage.py <command>

# Create superuser
sudo -u bibleteacher venv/bin/python manage.py createsuperuser

# Run migrations
sudo -u bibleteacher venv/bin/python manage.py migrate

# Collect static files
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput

# Create cache table
sudo -u bibleteacher venv/bin/python manage.py createcachetable bible_cache_table

# Django shell
sudo -u bibleteacher venv/bin/python manage.py shell

# Check deployment
sudo -u bibleteacher venv/bin/python manage.py check --deploy

# Show migrations
sudo -u bibleteacher venv/bin/python manage.py showmigrations
```

## Database Operations

### Backup

```bash
# Create backup
sudo -u postgres pg_dump bibleteacher > ~/backup_$(date +%Y%m%d_%H%M%S).sql

# Create compressed backup
sudo -u postgres pg_dump bibleteacher | gzip > ~/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Backup to specific location
sudo -u postgres pg_dump bibleteacher > /backups/bibleteacher_$(date +%Y%m%d).sql
```

### Restore

```bash
# Restore from backup
sudo -u postgres psql bibleteacher < backup_file.sql

# Restore from compressed backup
gunzip -c backup_file.sql.gz | sudo -u postgres psql bibleteacher

# Drop and recreate database before restore
sudo -u postgres dropdb bibleteacher
sudo -u postgres createdb bibleteacher
sudo -u postgres psql bibleteacher < backup_file.sql
```

### Database Access

```bash
# Connect to database
sudo -u postgres psql bibleteacher

# List databases
sudo -u postgres psql -l

# List tables
sudo -u postgres psql bibleteacher -c "\dt"

# Describe table
sudo -u postgres psql bibleteacher -c "\d table_name"

# Run SQL query
sudo -u postgres psql bibleteacher -c "SELECT * FROM auth_user;"
```

## File Permissions

### Fix Permissions

```bash
# Set ownership
sudo chown -R bibleteacher:bibleteacher /var/www/bibleteacher

# Set directory permissions
sudo chmod -R 755 /var/www/bibleteacher

# Set media directory permissions
sudo chmod -R 775 /var/www/bibleteacher/media

# Set log directory permissions
sudo chmod -R 775 /var/www/bibleteacher/logs

# Ensure www-data can access socket
sudo usermod -aG bibleteacher www-data
```

## SSL/TLS Management

### Certbot Commands

```bash
# Obtain certificate
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# Renew certificates
sudo certbot renew

# Test renewal (dry run)
sudo certbot renew --dry-run

# List certificates
sudo certbot certificates

# Revoke certificate
sudo certbot revoke --cert-path /etc/letsencrypt/live/your-domain.com/cert.pem

# Delete certificate
sudo certbot delete --cert-name your-domain.com
```

### Certificate Locations

```bash
# Certificate files
/etc/letsencrypt/live/your-domain.com/fullchain.pem
/etc/letsencrypt/live/your-domain.com/privkey.pem

# View certificate expiry
sudo certbot certificates
```

## Firewall (UFW)

### Basic Commands

```bash
# Status
sudo ufw status verbose

# Enable
sudo ufw enable

# Disable
sudo ufw disable

# Allow SSH
sudo ufw allow OpenSSH

# Allow HTTP
sudo ufw allow 80/tcp

# Allow HTTPS
sudo ufw allow 443/tcp

# Allow Nginx
sudo ufw allow 'Nginx Full'

# Delete rule
sudo ufw delete allow 80/tcp

# Reset firewall
sudo ufw reset
```

## Application Updates

### Update Code

```bash
# 1. Stop service
sudo systemctl stop bibleteacher.service

# 2. Backup current version
sudo cp -r /var/www/bibleteacher /var/www/bibleteacher.backup.$(date +%Y%m%d)

# 3. Pull new code (if using Git)
cd /var/www/bibleteacher
sudo -u bibleteacher git pull

# 4. Update dependencies
sudo -u bibleteacher venv/bin/pip install -r requirements.txt --upgrade

# 5. Run migrations
sudo -u bibleteacher venv/bin/python manage.py migrate

# 6. Collect static files
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput

# 7. Start service
sudo systemctl start bibleteacher.service

# 8. Check status
sudo systemctl status bibleteacher.service
```

### Rollback

```bash
# Stop service
sudo systemctl stop bibleteacher.service

# Restore backup
sudo rm -rf /var/www/bibleteacher
sudo mv /var/www/bibleteacher.backup.YYYYMMDD /var/www/bibleteacher

# Start service
sudo systemctl start bibleteacher.service
```

## Monitoring

### System Resources

```bash
# Disk usage
df -h

# Directory size
du -sh /var/www/bibleteacher/*

# Memory usage
free -h

# CPU usage
top

# Process list
ps aux | grep gunicorn
ps aux | grep nginx
```

### Application Health

```bash
# Check if socket exists
ls -l /run/gunicorn.sock

# Check if port 80 is listening
sudo netstat -tlnp | grep :80

# Check if port 443 is listening
sudo netstat -tlnp | grep :443

# Test application response
curl -I http://localhost

# Test with domain
curl -I http://your-domain.com
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status bibleteacher.service

# View recent logs
sudo journalctl -u bibleteacher.service -n 50

# Check socket
sudo systemctl status bibleteacher.socket
ls -l /run/gunicorn.sock

# Restart socket and service
sudo systemctl restart bibleteacher.socket
sudo systemctl restart bibleteacher.service
```

### 502 Bad Gateway

```bash
# Check Gunicorn is running
sudo systemctl status bibleteacher.service

# Check socket permissions
ls -l /run/gunicorn.sock

# Check Nginx error log
sudo tail -f /var/log/nginx/error.log

# Restart services
sudo systemctl restart bibleteacher.service
sudo systemctl restart nginx
```

### Static Files Not Loading

```bash
# Recollect static files
cd /var/www/bibleteacher
sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput

# Check permissions
sudo chmod -R 755 /var/www/bibleteacher/staticfiles

# Check Nginx config
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

### Database Connection Error

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
sudo -u postgres psql -c "SELECT 1"

# Check database exists
sudo -u postgres psql -l | grep bibleteacher

# Check user permissions
sudo -u postgres psql -c "\du bibleuser"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

## Performance Tuning

### Adjust Gunicorn Workers

```bash
# Edit gunicorn config
sudo nano /var/www/bibleteacher/gunicorn_conf.py

# Change workers value (recommended: 2-4 x CPU cores)
workers = 5

# Restart service
sudo systemctl restart bibleteacher.service
```

### Clear Django Cache

```bash
cd /var/www/bibleteacher
sudo -u bibleteacher venv/bin/python manage.py shell

# In Python shell:
from django.core.cache import cache
cache.clear()
exit()
```

## Useful One-Liners

```bash
# Restart everything
sudo systemctl restart bibleteacher.service && sudo systemctl reload nginx

# View all logs in real-time
sudo tail -f /var/www/bibleteacher/logs/*.log /var/log/nginx/*.log

# Check all service statuses
sudo systemctl status bibleteacher.service nginx postgresql

# Full application health check
sudo systemctl status bibleteacher.service && \
sudo systemctl status nginx && \
sudo systemctl status postgresql && \
curl -I http://localhost

# Quick backup
sudo -u postgres pg_dump bibleteacher > ~/backup_$(date +%Y%m%d_%H%M%S).sql && \
sudo tar -czf ~/media_backup_$(date +%Y%m%d_%H%M%S).tar.gz /var/www/bibleteacher/media/
```
