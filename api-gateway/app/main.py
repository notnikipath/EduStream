from __future__ import annotations

from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.edustream_common import CompletionWorkflowResult, Role, Settings, sign_token, verify_token


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8300

    course_service_url: str = "http://course-service:8301"
    learning_service_url: str = "http://learning-service:8302"
    test_service_url: str = "http://test-service:8303"
    webinar_service_url: str = "http://webinar-service:8304"
    gamification_service_url: str = "http://gamification-service:8305"
    analytics_service_url: str = "http://analytics-service:8306"
    notification_service_url: str = "http://notification-service:8307"

    jwt_secret: str = Settings().jwt_secret
    token_exp_minutes: int = 240

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="EduStream API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5175",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    user_id: str
    role: Role
    language: str = Field(default="ru", pattern="^(ru|en|kk)$")


class CompleteLessonRequest(BaseModel):
    user_id: str
    course_id: str
    lesson_id: str
    actor_role: Role


class QuizWorkflowRequest(BaseModel):
    quiz_id: str
    user_id: str
    course_id: str
    answers: dict[str, Any] = Field(default_factory=dict)
    actor_role: Role


AuthRequest.model_rebuild()
CompleteLessonRequest.model_rebuild()
QuizWorkflowRequest.model_rebuild()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "course": settings.course_service_url,
        "learning": settings.learning_service_url,
        "test": settings.test_service_url,
        "webinar": settings.webinar_service_url,
        "gamification": settings.gamification_service_url,
        "analytics": settings.analytics_service_url,
        "notification": settings.notification_service_url,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict[str, str]:
    token = sign_token(
        {"sub": request.user_id, "role": request.role.value, "language": request.language},
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict[str, Any]:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def service_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except HTTPException as exc:
                statuses[name] = {"status": "error", "detail": exc.detail}
            except httpx.HTTPError as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/workflow/complete-lesson")
async def complete_lesson_workflow(request: CompleteLessonRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        progress = await _post_json(
            client,
            f"{settings.learning_service_url}/progress/complete-lesson",
            request.model_dump(mode="json"),
        )
        await _post_json(
            client,
            f"{settings.analytics_service_url}/analytics/ingest/completion",
            {
                "user_id": request.user_id,
                "course_id": request.course_id,
                "completion_ratio": progress["completion_ratio"],
                "completed_lessons": len(progress["completed_lessons"]),
            },
        )
        await _post_json(
            client,
            f"{settings.gamification_service_url}/points/add",
            {
                "user_id": request.user_id,
                "course_id": request.course_id,
                "points": 40,
                "reason": f"Completed {request.lesson_id}",
                "actor_id": "SYSTEM",
                "actor_role": Role.ADMIN.value,
            },
        )

        certificate = None
        notification = None
        if progress["course_completed"]:
            course = await _get_json(client, f"{settings.course_service_url}/courses/{request.course_id}")
            certificate = await _post_json(
                client,
                f"{settings.gamification_service_url}/certificates/issue",
                {
                    "user_id": request.user_id,
                    "course_id": request.course_id,
                    "course_title": course["title"],
                    "actor_id": "SYSTEM",
                    "actor_role": Role.ADMIN.value,
                },
            )
            notification = await _post_json(
                client,
                f"{settings.notification_service_url}/notify/certificate",
                {
                    "user_id": request.user_id,
                    "certificate_url": certificate["url"],
                    "actor_role": Role.ADMIN.value,
                },
            )

    result = CompletionWorkflowResult(
        progress=progress,
        certificate=certificate,
        notification=notification,
        analytics={"course_id": request.course_id, "completion_ratio": progress["completion_ratio"]},
    )
    return result.model_dump(mode="json")


@app.post("/workflow/submit-quiz")
async def quiz_workflow(request: QuizWorkflowRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        submission = await _post_json(
            client,
            f"{settings.test_service_url}/submissions",
            {
                "quiz_id": request.quiz_id,
                "user_id": request.user_id,
                "answers": request.answers,
                "actor_role": request.actor_role.value,
            },
        )
        await _post_json(
            client,
            f"{settings.analytics_service_url}/analytics/ingest/quiz",
            {"course_id": request.course_id, "score_pct": submission["score_pct"]},
        )
        reward = await _post_json(
            client,
            f"{settings.gamification_service_url}/points/add",
            {
                "user_id": request.user_id,
                "course_id": request.course_id,
                "points": 70 if submission["passed"] else 20,
                "reason": f"Quiz {request.quiz_id} submitted",
                "actor_id": "SYSTEM",
                "actor_role": Role.ADMIN.value,
            },
        )
    return {"submission": submission, "reward": reward}


@app.get("/dashboard/{course_id}/{user_id}")
async def dashboard(course_id: str, user_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        course = await _get_json(client, f"{settings.course_service_url}/courses/{course_id}")
        learning = await _get_json(client, f"{settings.learning_service_url}/dashboard/{user_id}/{course_id}")
        webinars = await _get_json(client, f"{settings.webinar_service_url}/webinars", {"course_id": course_id})
        leaderboard = await _get_json(client, f"{settings.gamification_service_url}/leaderboard/{course_id}")
        profile = await _get_json(client, f"{settings.gamification_service_url}/profiles/{user_id}")
        analytics = await _get_json(
            client,
            f"{settings.analytics_service_url}/analytics/student/{user_id}",
            {"course_id": course_id},
        )
        course_analytics = await _get_json(
            client,
            f"{settings.analytics_service_url}/analytics/course/{course_id}",
            {"actor_role": Role.INSTRUCTOR.value},
        )
        kpi = await _get_json(client, f"{settings.analytics_service_url}/analytics/kpi")
        quizzes = await _get_json(client, f"{settings.test_service_url}/quizzes", {"course_id": course_id})

    return {
        "course": course,
        "learning": learning,
        "webinars": webinars,
        "leaderboard": leaderboard,
        "profile": profile,
        "analytics": analytics,
        "course_analytics": course_analytics,
        "kpi": kpi,
        "quizzes": quizzes,
    }
