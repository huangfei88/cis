# CIS — Centralised Infra Script Platform

A multi-user automated script execution platform with role-based access control, script review workflow, and isolated Docker sandbox execution.

## Architecture

```
Browser → Nginx (TLS) → FastAPI (Control Plane) → Redis Queue → Celery Worker → Docker Sandbox
                                                                                       ↓
                                                                              PostgreSQL + MinIO
```

## Features

- **JWT authentication** with refresh token rotation and Redis blacklist
- **RBAC**: `admin` / `reviewer` / `user` roles
- **Script review workflow**: pending → approved / rejected (human review required)
- **Ansible & shell script support** with static validation (module allow/deny list)
- **Isolated execution**: each task runs in an ephemeral Docker container with no network, read-only filesystem, dropped capabilities, and resource limits
- **Audit logging**: all operations recorded with who/what/when/IP
- **Vue 3 frontend** with real-time task polling

## Quick Start

```bash
cp .env.example .env          # configure secrets
cd execution/ansible-runner && docker build -t cis-runner:latest . && cd ../..
docker compose up -d
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full setup instructions.

## Security

See [docs/SECURITY.md](docs/SECURITY.md) for the threat model and mitigations.

## API

See [docs/API.md](docs/API.md) for endpoint documentation.

## Project Structure

```
cis/
├── backend/           FastAPI Control Plane + Celery worker
├── execution/         Sandbox image, seccomp profile, container config
├── frontend/          Vue 3 + Vite SPA
├── nginx/             TLS reverse proxy
├── docs/              API, security, deployment docs
└── docker-compose.yml Full stack deployment
```