# FileNest — VPS Deployment Guide

Tested on Ubuntu 22.04 (Hetzner). Adapt firewall commands for your cloud provider.

---

## 1. Initial Server Setup

```bash
apt update && apt upgrade -y
apt install -y curl git nginx certbot python3-certbot-nginx ufw
```

### Firewall

```bash
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

> Do **not** open port 9000 publicly — RustFS is accessed through nginx (see section 6).

---

## 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
```

---

## 3. Clone the Repo

```bash
git clone https://github.com/naveenraj-g/file-nest.git
cd file-nest
```

---

## 4. Create `.env` Files

Copy the examples and fill in values:

```bash
cp backend/.env.example backend/.env
cp iam/.env.example iam/.env
cp frontend/web/.env.example frontend/web/.env
```

Edit each file:

```bash
nano backend/.env
nano iam/.env
nano frontend/web/.env
```

Key things to set in `backend/.env`:
- All database, Redis, NATS connection strings use Docker service names (already set if you follow this guide)
- `RUSTFS_ENDPOINT_URL=http://rustfs:9000` — internal Docker hostname
- `RUSTFS_PUBLIC_URL=https://storage.yourdomain.com` — public HTTPS URL (see section 6)
- `IAM_URL=http://iam:5000` — internal Docker hostname

---

## 5. Pull and Start Core Services

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d postgres redis nats clamav rustfs iam backend
```

Check everything is running:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs backend --tail 50
```

Seed the IAM superadmin (first deploy only):

```bash
docker compose -f docker-compose.prod.yml exec iam pnpm seed:admin
```

---

## 6. Nginx — Subdomain Setup

Each service gets its own subdomain. Add A records in your DNS pointing all subdomains to the VPS IP before running certbot.

| Subdomain | Service | Internal port |
|-----------|---------|--------------|
| `filenest.iam.yourdomain.com` | IAM | 5000 |
| `filenest.api.yourdomain.com` | Backend | 8000 |
| `filenest.console.yourdomain.com` | Console | 3000 |
| `storage.yourdomain.com` | RustFS (S3) | 9000 |

### IAM

```bash
sudo nano /etc/nginx/sites-available/filenest-iam
```

```nginx
server {
    listen 80;
    server_name filenest.iam.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Backend

```bash
sudo nano /etc/nginx/sites-available/filenest-api
```

```nginx
server {
    listen 80;
    server_name filenest.api.yourdomain.com;

    client_max_body_size 0;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Console

```bash
sudo nano /etc/nginx/sites-available/filenest-console
```

```nginx
server {
    listen 80;
    server_name filenest.console.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### RustFS (storage) — required for presigned URLs to work in the browser

```bash
sudo nano /etc/nginx/sites-available/filenest-storage
```

```nginx
server {
    listen 80;
    server_name storage.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Required for large file uploads via presigned PUT
        client_max_body_size 0;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
```

### Enable all sites and get SSL

```bash
sudo ln -s /etc/nginx/sites-available/filenest-iam      /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/filenest-api      /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/filenest-console  /etc/nginx/sites-enabled/
sudo ln -s /etc/nginx/sites-available/filenest-storage  /etc/nginx/sites-enabled/

sudo nginx -t
sudo systemctl reload nginx

sudo certbot --nginx \
  -d filenest.iam.yourdomain.com \
  -d filenest.api.yourdomain.com \
  -d filenest.console.yourdomain.com \
  -d storage.yourdomain.com
```

After certbot runs, update `RUSTFS_PUBLIC_URL` in `backend/.env` to the HTTPS URL and restart the backend:

```bash
# edit backend/.env: RUSTFS_PUBLIC_URL=https://storage.yourdomain.com
docker compose -f docker-compose.prod.yml up -d backend
```

---

## 7. Console App — Deploying Updates

### CI/CD (IAM and Backend)

Pushing to `main` automatically builds and pushes the IAM and backend images to GHCR via GitHub Actions.

To pull the latest images on the VPS:

```bash
docker compose -f docker-compose.prod.yml pull iam backend
docker compose -f docker-compose.prod.yml up -d iam backend
```

### Console App — Local Build (Recommended)

The console has `NEXT_PUBLIC_*` env vars baked in at build time. GitHub Actions cannot reliably inject these into the Next.js bundle, so build the console image locally and push it to GHCR manually.

**On your local machine:**

```bash
# Log in to GHCR
echo <your-github-pat> | docker login ghcr.io -u <your-github-username> --password-stdin

# Build with the production env vars baked in
docker build \
  --build-arg NEXT_PUBLIC_BETTER_AUTH_URL=https://filenest.iam.yourdomain.com \
  --build-arg NEXT_PUBLIC_BETTER_AUTH_CLIENT_ID=<oauth-client-id> \
  --build-arg NEXT_PUBLIC_APP_URL=https://filenest.console.yourdomain.com \
  -t ghcr.io/naveenraj-g/file-nest/console:latest \
  ./frontend/web

# Push to GHCR
docker push ghcr.io/naveenraj-g/file-nest/console:latest
```

**On the VPS:**

```bash
docker compose -f docker-compose.prod.yml pull console
docker compose -f docker-compose.prod.yml --profile console up -d console
```

---

## 8. Starting the Console for the First Time

The console service uses a Docker Compose profile so it does not start automatically with the other services. Before starting it:

1. Create an OAuth client in the IAM admin panel (superadmin → OAuth Clients → Create)
2. Set redirect URI to `https://filenest.console.yourdomain.com/callback`
3. Copy the client ID — needed for the local build above

Then start it:

```bash
docker compose -f docker-compose.prod.yml --profile console up -d console
```

---

## 9. Updating Services

### Pull latest (IAM + Backend — built by CI)

```bash
git pull origin main
docker compose -f docker-compose.prod.yml pull iam backend
docker compose -f docker-compose.prod.yml up -d iam backend
```

### Console update

Rebuild locally (see section 7) then on VPS:

```bash
docker compose -f docker-compose.prod.yml pull console
docker compose -f docker-compose.prod.yml --profile console up -d console
```

---

## 10. Useful Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml logs backend -f
docker compose -f docker-compose.prod.yml logs iam -f

# Check container status
docker compose -f docker-compose.prod.yml ps

# Restart a single service
docker compose -f docker-compose.prod.yml restart backend

# Open a shell inside a container
docker compose -f docker-compose.prod.yml exec backend bash
docker compose -f docker-compose.prod.yml exec iam sh

# Check env vars inside a container
docker compose -f docker-compose.prod.yml exec backend env | grep RUSTFS

# Run database migrations manually
docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

# SSL cert renewal (runs automatically via systemd timer, manual test)
sudo certbot renew --dry-run
```

---

## 11. Verifying the Storage Setup

After everything is running, confirm presigned URLs use the public HTTPS domain:

```bash
# Should show RUSTFS_PUBLIC_URL=https://storage.yourdomain.com
docker compose -f docker-compose.prod.yml exec backend env | grep RUSTFS_PUBLIC_URL
```

Then upload a file via the console and confirm the download URL in the browser network tab starts with `https://storage.yourdomain.com`.
