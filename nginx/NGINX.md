# TicketRadar API — Nginx & Let's Encrypt HTTPS Setup Guide

This guide describes how to configure, deploy, and maintain the production Nginx reverse proxy and Let's Encrypt SSL/TLS certificates for the TicketRadar FastAPI backend on your host machine.

- **Production API URL:** `https://api.ticketradar.darkglance.in`
- **Internal Backend Target:** `http://127.0.0.1:8000` (Docker Container)

---

## Architecture Overview

```
                          Internet / Clients
                                  │
                                  │ HTTPS (443) / HTTP (80)
                                  ▼
                     ┌─────────────────────────┐
                     │     Nginx Host Server   │
                     │  api.ticketradar...     │
                     │  (SSL Termination &     │
                     │   Reverse Proxy)        │
                     └────────────┬────────────┘
                                  │ Proxy Pass
                                  │ http://127.0.0.1:8000
                                  ▼
                     ┌─────────────────────────┐
                     │  Docker API Container   │
                     │    ticketradar-api      │
                     │   FastAPI (Python 3.14) │
                     └─────────────────────────┘
```

- **Host Nginx (Port 80/443):** Terminates SSL via Let's Encrypt certificates, applies security headers, manages ACME challenges, and proxies traffic to `http://127.0.0.1:8000`.
- **Docker Container (`ticketradar-api`):** Runs FastAPI in Python 3.14 with Uvicorn, packages `.env` internally, and maps only to `127.0.0.1:8000` so it is protected behind Nginx.

---

## File Structure

```
TicketRadar/
├── docker-compose.yml                          # Docker Compose for FastAPI backend
├── Makefile                                    # Setup, Docker & Nginx targets
├── nginx/
│   ├── NGINX.md                               # This documentation file
│   ├── api.ticketradar.darkglance.in.conf     # Production Nginx site configuration
│   └── setup.sh                                # Automated Nginx & Let's Encrypt setup script
└── src/
    └── Backend/
        ├── Dockerfile                          # Backend Dockerfile (copies .env)
        ├── .dockerignore                       # Excludes build caches (retains .env)
        ├── .env                                # Backend secrets & configuration
        └── main.py                             # FastAPI entry point
```

---

## Prerequisites

Before running the setup on your host machine, ensure:

1. **DNS A Record Configured:**
   - The subdomain `api.ticketradar.darkglance.in` must resolve to the public IP address of your host machine.
   - Verify with: `dig +short api.ticketradar.darkglance.in` or `nslookup api.ticketradar.darkglance.in`.
2. **Inbound Firewall Ports Open:**
   - **Port 80 (TCP):** Required for Let's Encrypt ACME challenge verification.
   - **Port 443 (TCP):** Required for HTTPS traffic.
   - *Cloud Security Groups (AWS/GCP/DigitalOcean/Hetzner):* Ensure ports 80 and 443 allow incoming traffic from `0.0.0.0/0`.
   - *UFW (if enabled):* `sudo ufw allow 80/tcp && sudo ufw allow 443/tcp`.
3. **Docker & Docker Compose Installed:**
   - Ensure Docker Engine and the compose plugin are installed (`docker compose version`).
4. **Sudo / Root Privileges:**
   - Required for `make nginx-setup` to install Nginx and request Let's Encrypt certificates.

---

## Deployment Steps

### Step 1: Start the Dockerized API Backend

Make sure `src/Backend/.env` is configured with your Firebase, Twilio, and SMTP credentials.

```bash
# Build and start the container in detached mode
docker compose up -d --build

# View container logs:
docker compose logs -f ticketradar-api
```

Test that the container is responding locally on `127.0.0.1:8000`:
```bash
curl http://127.0.0.1:8000/health
# Response: {"status":"ok","service":"TicketRadar API","version":"0.1.0"}
```

### Step 2: Configure Host Nginx & Let's Encrypt SSL

Run the automated Nginx setup:

```bash
make nginx-setup
```

### What `make nginx-setup` Does Automatically:
1. Installs `nginx`, `certbot`, and `python3-certbot-nginx`.
2. Prepares ACME webroot challenge directory (`/var/www/certbot`).
3. Provisions a temporary HTTP bootstrap to obtain the Let's Encrypt SSL certificate for `api.ticketradar.darkglance.in`.
4. Copies the production configuration [nginx/api.ticketradar.darkglance.in.conf](file:///D:/PROGRAMMING/PROJECTS/TicketRadar/nginx/api.ticketradar.darkglance.in.conf) directly to `/etc/nginx/sites-available/`.
5. Enables the site and validates with `nginx -t`.
6. Reloads Nginx and activates the `certbot.timer` systemd timer for automatic renewals.

---

## Makefile Targets Reference

| Target | Command | Description |
|---|---|---|
| `nginx-setup` | `make nginx-setup` | Automated install of Nginx, Certbot, SSL certificates, and config. |
| `nginx-reload` | `make nginx-reload` | Runs `nginx -t` and reloads Nginx safely without downtime. |
| `nginx-cert-renew` | `make nginx-cert-renew` | Runs a dry-run renewal test with `certbot renew --dry-run`. |

---

## Verification & Testing

Once both the Docker container and Nginx are active:

### 1. Test Container Health Locally
```bash
curl http://127.0.0.1:8000/health
# Expected Output: {"status":"ok","service":"TicketRadar API","version":"0.1.0"}
```

### 2. Test HTTP to HTTPS Redirect
```bash
curl -I http://api.ticketradar.darkglance.in
# Expected Output: HTTP/1.1 301 Moved Permanently -> Location: https://api.ticketradar.darkglance.in/
```

### 3. Test HTTPS API Endpoint Publicly
```bash
curl -I https://api.ticketradar.darkglance.in/health
# Expected Output: HTTP/2 200 OK
```

---

## SSL Certificate Maintenance & Auto-Renewal

Let's Encrypt certificates expire after 90 days. Certbot automatically renews them via the systemd `certbot.timer`.

- **Check active certificates:**
  ```bash
  sudo certbot certificates
  ```
- **Test automated renewal:**
  ```bash
  make nginx-cert-renew
  # or: sudo certbot renew --dry-run
  ```
- **Force renewal (if needed):**
  ```bash
  sudo certbot renew --force-renewal
  make nginx-reload
  ```

---

## Logs & Monitoring

| Component | Log Command / File |
|---|---|
| **API Docker Container** | `docker compose logs -f ticketradar-api` |
| **Nginx Access Log** | `tail -f /var/log/nginx/ticketradar_api_access.log` |
| **Nginx Error Log** | `tail -f /var/log/nginx/ticketradar_api_error.log` |
| **Certbot Renewal Log** | `tail -f /var/log/letsencrypt/letsencrypt.log` |
