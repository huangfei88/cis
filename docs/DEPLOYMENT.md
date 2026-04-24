# Deployment Guide

## Prerequisites
- Docker Engine 24+ and Docker Compose v2
- A domain name with DNS pointing to your server
- TLS certificate (Let's Encrypt or corporate CA)

## Setup

### 1. Clone and configure
```bash
git clone https://github.com/huangfei88/cis.git
cd cis
cp .env.example .env
# Edit .env and set strong passwords for all secrets
```

### 2. Generate a SECRET_KEY
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```
Paste the output into `.env` as `SECRET_KEY`.

### 3. TLS Certificates
```bash
# Create the named volume used by Nginx
docker volume create cis_nginx_certs
# Copy your certificates into the volume
docker run --rm -v cis_nginx_certs:/certs alpine sh -c \
  "cp /path/to/server.crt /certs/ && cp /path/to/server.key /certs/"
```

### 4. Build the execution image
```bash
cd execution/ansible-runner
docker build -t cis-runner:latest .
cd ../..
```

### 5. Start the stack
```bash
docker compose up -d
```

### 6. Verify
```bash
docker compose ps          # all services should be healthy
curl https://<host>/health
```

## Upgrading
```bash
docker compose pull
docker compose up -d --build
```

## Environment Variables

See `backend/.env.example` for a full list. Critical variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | 32-byte hex string for JWT signing |
| `POSTGRES_PASSWORD` | PostgreSQL password |
| `REDIS_PASSWORD` | Redis AUTH password |
| `MINIO_SECRET_KEY` | MinIO root password |

## Security Checklist

- [ ] All passwords changed from example values
- [ ] `APP_ENV=production` set (disables /docs UI)
- [ ] TLS certificate valid and HSTS enabled
- [ ] Firewall: only ports 80/443 open externally
- [ ] Docker socket access restricted to worker container only
- [ ] Regular backup of `postgres_data` volume
