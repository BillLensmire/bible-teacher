# Automated Deployment to Akamai (Linode)

This document describes how to set up automated deployment of the Bible Teacher Django application to an Akamai Connected Cloud (formerly Linode) Linux node.

## Overview

The deployment pipeline uses:
- **Initial provisioning**: `install.sh` script run once on the server
- **Code updates**: Git-based deployment triggered from GitHub Actions
- **Server stack**: PostgreSQL + Gunicorn + Nginx on Ubuntu/Debian

## Prerequisites

- Akamai/Linode account
- GitHub repository for this project
- Domain name (optional but recommended)

---

## Step 1: Create the Akamai Instance

1. Log in to [Akamai Cloud Manager](https://cloud.linode.com/)
2. Create a new Linode:
   - **Image**: Ubuntu 24.04 LTS (or 22.04 LTS)
   - **Region**: Choose one close to your users
   - **Plan**: Shared CPU, 2 GB RAM / 1 CPU (minimum), or 4 GB RAM for production
   - **Label**: `bibleteacher-prod`
   - **Root password**: Generate a strong password (you will disable password auth later)
   - **SSH key**: Add your local SSH public key (`cat ~/.ssh/id_rsa.pub`)
3. Note the public IPv4 address after creation

### Configure Akamai Cloud Firewall (Recommended)

In Akamai Cloud Manager:
1. Go to **Firewalls** → **Create Firewall**
2. Attach it to your Linode
3. Add inbound rules:
   - **SSH (22)**: `LIMIT` to your IP only
   - **HTTP (80)**: `ACCEPT` from `All IPv4, All IPv6`
   - **HTTPS (443)**: `ACCEPT` from `All IPv4, All IPv6`
4. Default policy: `DROP`

---

## Step 2: Initial Server Provisioning

SSH into your new server and run the installation script.

```bash
# On your local machine
ssh root@YOUR_SERVER_IP
```

On the server:

```bash
# Update system
apt update && apt upgrade -y

# Install git
apt install -y git

# Clone the repository
mkdir -p /opt && cd /opt
git clone https://github.com/YOUR_USERNAME/bible-teacher.git bibleteacher

# Create install config
cd /opt/bibleteacher
cp install.config.example install.config
nano install.config
```

Edit `install.config` with at minimum:
- `DB_PASSWORD`: A strong PostgreSQL password
- `DOMAIN`: Your domain name (leave blank for IP-only)
- `SETUP_SSL`: `y` if you have a domain and want HTTPS, otherwise `n`
- `ADMIN_EMAIL`: Required if `SETUP_SSL=y`

Run the installation:

```bash
cd /opt/bibleteacher
sudo bash install.sh
```

This script installs and configures:
- PostgreSQL database and user
- Python virtual environment and dependencies
- Django migrations, static files, and cache table
- Gunicorn systemd service and socket
- Nginx reverse proxy
- UFW firewall
- SSL certificate via Let's Encrypt (if configured)

Verify the application is running:

```bash
sudo systemctl status bibleteacher.service
sudo systemctl status nginx
```

Visit `http://YOUR_SERVER_IP` in a browser.

---

## Step 3: Set Up Automated Deployments via GitHub Actions

This workflow deploys automatically whenever you push to the `main` branch.

### 3.1. Create a Deploy User on the Server

```bash
# On the server
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG bibleteacher deploy
```

### 3.2. Add Server Secrets to GitHub

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Name | Value |
|-------------|-------|
| `DEPLOY_HOST` | Your server IP address |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | Contents of `~/.ssh/deploy_key` (see below) |

Generate a deploy SSH key (on your local machine):

```bash
ssh-keygen -t ed25519 -f ~/.ssh/bibleteacher_deploy -C "github-actions-deploy"
# Do NOT set a passphrase
cat ~/.ssh/bibleteacher_deploy.pub
```

Copy the public key to the server:

```bash
# On the server
sudo mkdir -p /home/deploy/.ssh
sudo bash -c 'echo "PASTE_PUBLIC_KEY_HERE" > /home/deploy/.ssh/authorized_keys'
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Copy the **private** key to GitHub as the `DEPLOY_SSH_KEY` secret:

```bash
cat ~/.ssh/bibleteacher_deploy
```

### 3.3. Create the GitHub Actions Workflow

Create `.github/workflows/deploy.yml` in your repository:

```yaml
name: Deploy to Akamai

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            set -e
            cd /opt/bibleteacher
            sudo -u bibleteacher git pull origin main
            sudo -u bibleteacher venv/bin/pip install -r requirements.txt
            sudo -u bibleteacher venv/bin/python manage.py migrate --noinput
            sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput
            sudo systemctl restart bibleteacher.service
            echo "Deployment complete at $(date)"
```

Commit and push:

```bash
git add .github/workflows/deploy.yml
git commit -m "Add automated deployment to Akamai"
git push origin main
```

The first push will trigger the workflow. Check progress in GitHub under **Actions**.

---

## Step 4: Manual Deployment (Alternative)

If you prefer not to use GitHub Actions, use the included `deploy.sh` script from your local machine.

### 4.1. Configure Local Deploy Script

Copy and edit the configuration:

```bash
cp deployment/deploy.env.example deployment/deploy.env
nano deployment/deploy.env
```

Set:
- `DEPLOY_HOST`: Your server IP
- `DEPLOY_USER`: `deploy` (or your SSH user)
- `APP_DIR`: `/opt/bibleteacher`
- `APP_USER`: `bibleteacher`

### 4.2. Run the Deploy Script

```bash
bash deployment/deploy.sh
```

This script:
1. SSHs into the server
2. Pulls the latest code from `main`
3. Installs updated Python dependencies
4. Runs Django migrations
5. Collects static files
6. Restarts the Gunicorn service

---

## Step 5: Post-Deployment Verification

After any deployment, verify:

```bash
# On the server
sudo systemctl status bibleteacher.service
sudo tail -n 20 /opt/bibleteacher/logs/django.log
sudo tail -n 20 /opt/bibleteacher/logs/gunicorn_error.log
sudo nginx -t
```

Check the site in a browser and test:
- Home page loads
- Admin login works
- Static files (CSS, images) load correctly
- Media uploads function

---

## Step 6: Security Hardening

Complete these steps after the first successful deployment:

### Disable Root Password Login

```bash
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Set Up Automatic Security Updates

```bash
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Select "Yes"
```

### Enable Fail2ban

```bash
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Set Up Database Backups

Create a backup script:

```bash
sudo tee /opt/bibleteacher/scripts/backup.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/bibleteacher/backups"
DB_NAME="bibleteacher"
mkdir -p "$BACKUP_DIR"
pg_dump -U bibleuser -h localhost "$DB_NAME" > "$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql"
find "$BACKUP_DIR" -name "db_*.sql" -mtime +7 -delete
EOF

sudo chmod +x /opt/bibleteacher/scripts/backup.sh
sudo mkdir -p /opt/bibleteacher/scripts
```

Add a cron job:

```bash
sudo crontab -e
# Add:
0 2 * * * /opt/bibleteacher/scripts/backup.sh
```

---

## Directory Reference

| Path | Purpose |
|------|---------|
| `/opt/bibleteacher` | Application root |
| `/opt/bibleteacher/venv` | Python virtual environment |
| `/opt/bibleteacher/logs` | Application logs |
| `/opt/bibleteacher/staticfiles` | Collected static assets |
| `/opt/bibleteacher/media` | User-uploaded files |
| `/etc/nginx/sites-available/bibleteacher` | Nginx config |
| `/etc/systemd/system/bibleteacher.service` | Gunicorn service |
| `/etc/systemd/system/bibleteacher.socket` | Gunicorn socket |
| `/opt/bibleteacher/backups` | Database backups |

---

## Troubleshooting

### Deployment fails with permission denied
- Ensure the deploy user is in the `bibleteacher` group: `sudo usermod -aG bibleteacher deploy`
- Check `/opt/bibleteacher` ownership: `sudo chown -R bibleteacher:bibleteacher /opt/bibleteacher`

### Gunicorn fails to restart
```bash
sudo journalctl -u bibleteacher.service -n 50
sudo tail -f /opt/bibleteacher/logs/gunicorn_error.log
```

### Static files not updating
```bash
sudo -u bibleteacher /opt/bibleteacher/venv/bin/python /opt/bibleteacher/manage.py collectstatic --noinput --clear
sudo systemctl restart nginx
```

### Database migration fails
```bash
sudo -u bibleteacher /opt/bibleteacher/venv/bin/python /opt/bibleteacher/manage.py migrate --noinput
sudo -u bibleteacher /opt/bibleteacher/venv/bin/python /opt/bibleteacher/manage.py showmigrations
```

---

## Summary

1. **One-time setup**: Run `install.sh` on the Akamai server to provision everything
2. **Ongoing updates**: Push to `main` on GitHub triggers automatic deployment via Actions
3. **Manual fallback**: Use `deployment/deploy.sh` if you need to deploy outside of GitHub

For the initial manual installation details, see `MANUAL_INSTALLATION.md`.
For day-to-day commands, see `deployment/QUICK_REFERENCE.md`.
