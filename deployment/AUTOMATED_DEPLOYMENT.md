## Automated Deployment to Akamai (Linode)

This document describes how to set up automated deployment of the Bible Teacher Django application to an Akamai Connected Cloud (formerly Linode) Linux node.

## Overview

The deployment pipeline uses:

*   **Initial provisioning**: `install.sh` script run once on the server
*   **Code updates**: Git-based deployment triggered from GitHub Actions
*   **Server stack**: PostgreSQL + Gunicorn + Nginx on Ubuntu/Debian

## Prerequisites

*   Akamai/Linode account
*   GitHub repository for this project
*   Domain name (optional but recommended)

## Step 1: Create the Akamai Instance

1.  Log in to [Akamai Cloud Manager](https://cloud.linode.com/)
2.  Create a new Linode:
    *   **Image**: Ubuntu 24.04 LTS (or 22.04 LTS)
    *   **Region**: Choose one close to your users
    *   **Plan**: Shared CPU, 2 GB RAM / 1 CPU (minimum), or 4 GB RAM for production
    *   **Label**: `bibleteacher-prod`
    *   **Root password**: Generate a strong password (you will disable password auth later)
    *   **SSH key**: Add your local SSH public key (`cat ~/.ssh/id_rsa.pub`)
3.  Note the public IPv4 address after creation

### Configure Akamai Cloud Firewall (Recommended)

In Akamai Cloud Manager:

1.  Go to **Firewalls** → **Create Firewall**
2.  Attach it to your Linode
3.  Add inbound rules:
    *   **SSH (22)**: `LIMIT` to your IP only
    *   **HTTP (80)**: `ACCEPT` from `All IPv4, All IPv6`
    *   **HTTPS (443)**: `ACCEPT` from `All IPv4, All IPv6`
4.  Default policy: `DROP`

## Step 2: Initial Server Provisioning

SSH into your new server and run the installation script.

```plaintext
# On your local machine
ssh root@YOUR_SERVER_IP
```

On the server:

```plaintext
# Update system
apt update &amp;&amp; apt upgrade -y

# Install git
apt install -y git

# Clone the repository
mkdir -p /opt &amp;&amp; cd /opt
git clone https://github.com/YOUR_USERNAME/bible-teacher.git bibleteacher

# Create install config
cd /var/www/bibleteacher
cp install.config.example install.config
nano install.config
```

Edit `install.config` with at minimum:

*   `DB_PASSWORD`: A strong PostgreSQL password
*   `DOMAIN`: Your domain name (leave blank for IP-only)
*   `SETUP_SSL`: `y` if you have a domain and want HTTPS, otherwise `n`
*   `ADMIN_EMAIL`: Required if `SETUP_SSL=y`

Run the installation:

```plaintext
cd /var/www/bibleteacher
sudo bash install.sh
```

This script installs and configures:

*   PostgreSQL database and user
*   Python virtual environment and dependencies
*   Django migrations, static files, and cache table
*   Gunicorn systemd service and socket
*   Nginx reverse proxy
*   UFW firewall
*   SSL certificate via Let's Encrypt (if configured)

Verify the application is running:

```plaintext
sudo systemctl status bibleteacher.service
sudo systemctl status nginx
```

Visit `http://YOUR_SERVER_IP` in a browser.

## Step 3: Set Up Automated Deployments via GitHub Actions

This workflow deploys automatically whenever you push to the `main` branch.

### 3.1. Create a Deploy User on the Server

```plaintext
# On the server
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG bibleteacher deploy
```

### 3.2. Add Server Secrets to GitHub

In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**:

| Secret Name | Value |
| --- | --- |
| `DEPLOY_HOST` | Your server IP address |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | Contents of `~/.ssh/deploy_key` (see below) |

Generate a deploy SSH key (on your local machine):

```plaintext
ssh-keygen -t ed25519 -f ~/.ssh/bibleteacher_deploy -C "github-actions-deploy"
# Do NOT set a passphrase
cat ~/.ssh/bibleteacher_deploy.pub
```

Copy the public key to the server:

```plaintext
# On the server
sudo mkdir -p /home/deploy/.ssh
sudo bash -c 'echo "PASTE_PUBLIC_KEY_HERE" &gt; /home/deploy/.ssh/authorized_keys'
sudo chown -R deploy:deploy /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
```

Copy the **private** key to GitHub as the `DEPLOY_SSH_KEY` secret:

```plaintext
cat ~/.ssh/bibleteacher_deploy
```

### 3.3. Create the GitHub Actions Workflow

Create `.github/workflows/deploy.yml` in your repository:

```plaintext
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
            cd /var/www/bibleteacher
            sudo -u bibleteacher git pull origin main
            sudo -u bibleteacher venv/bin/pip install -r requirements.txt
            sudo -u bibleteacher venv/bin/python manage.py migrate --noinput
            sudo -u bibleteacher venv/bin/python manage.py collectstatic --noinput
            sudo systemctl restart bibleteacher.service
            echo "Deployment complete at $(date)"
```

Commit and push:

```plaintext
git add .github/workflows/deploy.yml
git commit -m "Add automated deployment to Akamai"
git push origin main
```

The first push will trigger the workflow. Check progress in GitHub under **Actions**.

## Step 4: Manual Deployment (Alternative)

If you prefer not to use GitHub Actions, use the included `deploy.sh` script from your local machine.

### 4.1. Configure Local Deploy Script

Copy and edit the configuration:

```plaintext
cp deployment/deploy.env.example deployment/deploy.env
nano deployment/deploy.env
```

Set:

*   `DEPLOY_HOST`: Your server IP
*   `DEPLOY_USER`: `deploy` (or your SSH user)
*   `APP_DIR`: `/var/www/bibleteacher`
*   `APP_USER`: `www-data`

### 4.2. Run the Deploy Script

```plaintext
bash deployment/deploy.sh
```

This script:

1.  SSHs into the server
2.  Pulls the latest code from `main`
3.  Installs updated Python dependencies
4.  Runs Django migrations
5.  Collects static files
6.  Restarts the Gunicorn service

## Step 5: Post-Deployment Verification

After any deployment, verify:

```plaintext
# On the server
sudo systemctl status bibleteacher.service
sudo tail -n 20 /var/www/bibleteacher/logs/django.log
sudo tail -n 20 /var/www/bibleteacher/logs/gunicorn_error.log
sudo nginx -t
```

Check the site in a browser and test:

*   Home page loads
*   Admin login works
*   Static files (CSS, images) load correctly
*   Media uploads function

## Step 6: Security Hardening

Complete these steps after the first successful deployment:

### Disable Root Password Login

```plaintext
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo sed -i 's/PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

### Set Up Automatic Security Updates

```plaintext
sudo apt install -y unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
# Select "Yes"
```

### Enable Fail2ban

```plaintext
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Set Up Database Backups

Create a backup script:

```plaintext
sudo tee /var/www/bibleteacher/scripts/backup.sh &lt;&lt; 'EOF'
#!/bin/bash
BACKUP_DIR="/var/www/bibleteacher/backups"
DB_NAME="bibleteacher"
mkdir -p "$BACKUP_DIR"
pg_dump -U bibleuser -h localhost "$DB_NAME" &gt; "$BACKUP_DIR/db_$(date +%Y%m%d_%H%M%S).sql"
find "$BACKUP_DIR" -name "db_*.sql" -mtime +7 -delete
EOF

sudo chmod +x /var/www/bibleteacher/scripts/backup.sh
sudo mkdir -p /var/www/bibleteacher/scripts
```

Add a cron job:

```plaintext
sudo crontab -e
# Add:
0 2 * * * /var/www/bibleteacher/scripts/backup.sh
```

## Directory Reference

| Path | Purpose |
| --- | --- |
| `/var/www/bibleteacher` | Application root |
| `/var/www/bibleteacher/venv` | Python virtual environment |
| `/var/www/bibleteacher/logs` | Application logs |
| `/var/www/bibleteacher/staticfiles` | Collected static assets |
| `/var/www/bibleteacher/media` | User-uploaded files |
| `/etc/nginx/sites-available/bibleteacher` | Nginx config |
| `/etc/systemd/system/bibleteacher.service` | Gunicorn service |
| `/etc/systemd/system/bibleteacher.socket` | Gunicorn socket |
| `/var/www/bibleteacher/backups` | Database backups |

## Troubleshooting

### Deployment fails with permission denied

*   Ensure the deploy user is in the `bibleteacher` group: `sudo usermod -aG bibleteacher deploy`
*   Check `/var/www/bibleteacher` ownership: `sudo chown -R bibleteacher:bibleteacher /var/www/bibleteacher`

### Gunicorn fails to restart

```plaintext
sudo journalctl -u bibleteacher.service -n 50
sudo tail -f /var/www/bibleteacher/logs/gunicorn_error.log
```

### Static files not updating

```plaintext
sudo -u bibleteacher /var/www/bibleteacher/venv/bin/python /var/www/bibleteacher/manage.py collectstatic --noinput --clear
sudo systemctl restart nginx
```

### Database migration fails

```plaintext
sudo -u bibleteacher /var/www/bibleteacher/venv/bin/python /var/www/bibleteacher/manage.py migrate --noinput
sudo -u bibleteacher /var/www/bibleteacher/venv/bin/python /var/www/bibleteacher/manage.py showmigrations
```

## Summary

1.  **One-time setup**: Run `install.sh` on the Akamai server to provision everything
2.  **Ongoing updates**: Push to `main` on GitHub triggers automatic deployment via Actions
3.  **Manual fallback**: Use `deployment/deploy.sh` if you need to deploy outside of GitHub

For the initial manual installation details, see `MANUAL_INSTALLATION.md`.  
For day-to-day commands, see `deployment/QUICK_REFERENCE.md`.