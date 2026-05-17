# EduStream Architecture

## Overview
EduStream uses FastAPI microservices connected through an API gateway. The platform covers the full learning lifecycle: course creation, enrollment, lesson completion, testing, webinar delivery, gamification, analytics, and notifications.

## Services
- `api-gateway`: auth, aggregated dashboard, workflow orchestration.
- `course-service`: course catalog, modules, lessons, media asset binding.
- `learning-service`: enrollments, progress tracking, comments, adaptive recommendations.
- `test-service`: quizzes, submissions, essay grading, parallel grading hints.
- `webinar-service`: webinar scheduling, chat, polls, recording links, Zoom/YouTube sync.
- `gamification-service`: points, achievements, certificates, leaderboard.
- `analytics-service`: student and course KPIs, recommendation accuracy, video-start estimates.
- `notification-service`: certificate and webinar reminders.

## Data Plane
- PostgreSQL: transactional data and reference entities.
- Redis: cache and lightweight event fan-out.
- MinIO: recording links, certificates, uploaded learning assets.

## Main Workflow
1. Student completes a lesson through the gateway.
2. `learning-service` updates completion state.
3. `analytics-service` ingests completion metrics.
4. `gamification-service` awards points.
5. If the course is finished, a certificate is issued and `notification-service` sends delivery info.

## Scaling Notes
- Gateway and stateless services scale horizontally.
- Webinar nodes can be balanced based on active sessions and viewer targets.
- Parallel grading hints allow distribution of test processing across workers.
- Recommendation and KPI endpoints are cache-friendly and suitable for Redis.
