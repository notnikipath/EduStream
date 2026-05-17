# API Summary

## Gateway
- `GET /health`
- `GET /services/health`
- `POST /auth/token`
- `POST /auth/verify`
- `POST /workflow/complete-lesson`
- `POST /workflow/submit-quiz`
- `GET /dashboard/{course_id}/{user_id}`

## Course Service
- `GET /courses`
- `GET /courses/{course_id}`
- `GET /courses/{course_id}/catalog`
- `POST /courses`
- `POST /courses/{course_id}/modules`
- `POST /courses/{course_id}/lessons`
- `POST /courses/{course_id}/assets`

## Learning Service
- `POST /enrollments`
- `POST /progress/complete-lesson`
- `GET /dashboard/{user_id}/{course_id}`
- `POST /recommendations`
- `GET /dropout-risk/{user_id}/{course_id}`

## Test Service
- `GET /quizzes`
- `POST /quizzes`
- `POST /submissions`
- `POST /essays/grade`
- `POST /grading/parallel-plan`

## Webinar Service
- `GET /webinars`
- `POST /webinars`
- `POST /webinars/{webinar_id}/join`
- `POST /webinars/{webinar_id}/polls`
- `POST /integrations/zoom/import`
- `POST /integrations/youtube/publish`

## Gamification Service
- `POST /points/add`
- `POST /certificates/issue`
- `GET /leaderboard/{course_id}`
- `GET /profiles/{user_id}`

## Analytics Service
- `POST /analytics/ingest/completion`
- `POST /analytics/ingest/quiz`
- `POST /analytics/recommendation-accuracy`
- `GET /analytics/student/{user_id}`
- `GET /analytics/course/{course_id}`
- `GET /analytics/kpi`
