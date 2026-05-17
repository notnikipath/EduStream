# Deployment Guide

## Local Environment
1. Install Docker and Docker Compose.
2. Open the project root `task_10`.
3. Run `docker compose up --build -d`.
4. Check `http://localhost:8380/services/health`.
5. Open the frontend at `http://localhost:5176`.

## Containers And Ports
- Gateway: `8380 -> 8300`
- Frontend: `5176 -> 5176`
- PostgreSQL: `55434 -> 5432`
- Redis: `6382 -> 6379`
- MinIO API: `9300`
- MinIO Console: `9301`

## CI/CD
- CI runs Ruff, pytest, and `docker compose config`.
- CD builds service images for the eight backend containers.

## Operational Notes
- Update `.env` for secrets in non-demo environments.
- Replace demo URLs with production S3/CDN endpoints.
- Add external media infrastructure for WebRTC/HLS in production.
