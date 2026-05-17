# EduStream

EduStream is a microservice-based online education platform for courses, webinars, testing, gamification, analytics, and certificate delivery.

## Services
- `api-gateway`
- `course-service`
- `learning-service`
- `test-service`
- `webinar-service`
- `gamification-service`
- `analytics-service`
- `notification-service`
- `frontend`

## Optional Improvements Implemented
- Adaptive learning recommendations
- Automated essay grading
- Student dropout risk prediction
- Zoom and YouTube webinar integrations
- Parallel grading planning
- Webinar capacity balancing

## Local Run
1. `cd task_10`
2. `docker compose up --build -d`
3. Gateway: `http://localhost:8380/health`
4. Frontend: `http://localhost:5176`

## Quality Checks
- `python -m ruff check .`
- `python -m pytest -q`
- `docker compose config`

## Demo Flow
Run `python scripts/demo_pipeline.py` after the stack is up to simulate lesson completion, analytics ingest, gamification reward, and optional certificate issuance.
