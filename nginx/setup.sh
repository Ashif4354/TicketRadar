#!/usr/bin/env bash
# ==============================================================================
# TicketRadar API - Automated Nginx & Let's Encrypt Setup Script
# Target Domain: api.ticketradar.darkglance.in
# Target Backend: http://127.0.0.1:8000
# ==============================================================================

set -euo pipefail

# Configuration
DOMAIN="api.ticketradar.darkglance.in"
EMAIL="darkglance.developer@gmail.com"
BACKEND_PORT="8000"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONF_SOURCE="${SCRIPT_DIR}/api.ticketradar.darkglance.in.conf"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 1. Verify root or sudo privilege
if [[ $EUID -ne 0 ]]; then
    if command -v sudo >/dev/null 2>&1; then
        log_info "Elevating to sudo privileges..."
        exec sudo bash "$0" "$@"
    else
        log_error "This script requires root privileges. Please run as root or with sudo."
        exit 1
    fi
fi

log_info "Starting Nginx & SSL setup for domain: ${DOMAIN}"
log_info "Let's Encrypt Email: ${EMAIL}"
log_info "Backend Proxy Target: http://127.0.0.1:${BACKEND_PORT}"

# 2. Package installation based on distribution
install_packages() {
    log_info "Checking and installing dependencies (nginx, certbot)..."

    if command -v apt-get >/dev/null 2>&1; then
        export DEBIAN_FRONTEND=noninteractive
        apt-get update -y
        apt-get install -y nginx certbot python3-certbot-nginx curl
    elif command -v dnf >/dev/null 2>&1; then
        dnf install -y epel-release || true
        dnf install -y nginx certbot python3-certbot-nginx curl
    elif command -v yum >/dev/null 2>&1; then
        yum install -y epel-release || true
        yum install -y nginx certbot python3-certbot-nginx curl
    elif command -v pacman >/dev/null 2>&1; then
        pacman -Sy --noconfirm nginx certbot certbot-nginx curl
    else
        log_warn "Unknown package manager. Ensuring nginx and certbot are installed manually."
        if ! command -v nginx >/dev/null 2>&1 || ! command -v certbot >/dev/null 2>&1; then
            log_error "nginx or certbot is missing. Please install them and rerun this script."
            exit 1
        fi
    fi
}

install_packages

# 3. Create ACME challenge webroot directory
log_info "Configuring ACME webroot directory at /var/www/certbot..."
mkdir -p /var/www/certbot
chown -R www-data:www-data /var/www/certbot 2>/dev/null || chown -R nginx:nginx /var/www/certbot 2>/dev/null || true
chmod -R 755 /var/www/certbot

# Determine Nginx config directories (Debian/Ubuntu sites-available vs RHEL/CentOS conf.d)
USE_SITES_AVAILABLE=false
if [[ -d "/etc/nginx/sites-available" && -d "/etc/nginx/sites-enabled" ]]; then
    USE_SITES_AVAILABLE=true
    AVAILABLE_DIR="/etc/nginx/sites-available"
    ENABLED_DIR="/etc/nginx/sites-enabled"
else
    AVAILABLE_DIR="/etc/nginx/conf.d"
    ENABLED_DIR="/etc/nginx/conf.d"
fi

# Disable default nginx configuration if present to avoid port 80 collisions
if [[ -f "/etc/nginx/sites-enabled/default" ]]; then
    log_info "Disabling default Nginx site configuration..."
    rm -f /etc/nginx/sites-enabled/default
fi

# 4. Check for existing Let's Encrypt certificates
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
KEY_PATH="/etc/letsencrypt/live/${DOMAIN}/privkey.pem"

if [[ ! -f "$CERT_PATH" || ! -f "$KEY_PATH" ]]; then
    log_info "SSL certificates for ${DOMAIN} not found. Deploying temporary HTTP bootstrap configuration..."

    BOOTSTRAP_CONF="${AVAILABLE_DIR}/ticketradar-bootstrap.conf"
    cat <<EOF > "$BOOTSTRAP_CONF"
server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
        allow all;
    }

    location / {
        return 200 "TicketRadar SSL Bootstrap in progress. Domain validation pending.\n";
        add_header Content-Type text/plain;
    }
}
EOF

    if [[ "$USE_SITES_AVAILABLE" == "true" ]]; then
        ln -sf "$BOOTSTRAP_CONF" "${ENABLED_DIR}/ticketradar-bootstrap.conf"
    fi

    log_info "Testing bootstrap configuration and reloading Nginx..."
    nginx -t
    systemctl restart nginx || systemctl start nginx

    log_info "Requesting Let's Encrypt certificate for ${DOMAIN} via certbot..."
    certbot certonly --webroot \
        -w /var/www/certbot \
        -d "${DOMAIN}" \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        --non-interactive

    # Clean up bootstrap config
    if [[ "$USE_SITES_AVAILABLE" == "true" ]]; then
        rm -f "${ENABLED_DIR}/ticketradar-bootstrap.conf"
    fi
    rm -f "$BOOTSTRAP_CONF"
else
    log_info "Existing SSL certificate found at ${CERT_PATH}."
fi

# 5. Install production Nginx configuration (copied directly)
TARGET_CONF="${AVAILABLE_DIR}/${DOMAIN}.conf"
log_info "Copying production configuration directly to ${TARGET_CONF}..."
cp "$CONF_SOURCE" "$TARGET_CONF"

if [[ "$USE_SITES_AVAILABLE" == "true" ]]; then
    ln -sf "$TARGET_CONF" "${ENABLED_DIR}/${DOMAIN}.conf"
fi

# 6. Verify configuration and reload Nginx
log_info "Validating production Nginx configuration..."
nginx -t

log_info "Enabling and reloading Nginx service..."
systemctl enable nginx
systemctl reload nginx || systemctl restart nginx

# 7. Enable automated certificate renewal
if systemctl list-unit-files | grep -q certbot.timer; then
    log_info "Ensuring systemd certbot renewal timer is active..."
    systemctl enable --now certbot.timer
fi

log_success "=================================================================="
log_success " Nginx & SSL setup successfully completed!"
log_success " Domain:  https://${DOMAIN}"
log_success " Backend: http://127.0.0.1:${BACKEND_PORT}"
log_success " Config:  ${TARGET_CONF}"
log_success " Test:    curl -I https://${DOMAIN}/health"
log_success "=================================================================="
