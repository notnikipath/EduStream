from __future__ import annotations

from statistics import mean
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.edustream_common import (
    Role,
    Settings,
    course_effectiveness,
    dropout_risk,
    estimate_video_start_seconds,
    has_permission,
    recommendation_accuracy,
)

settings = Settings(service_name="analytics-service", service_port=8306)
app = FastAPI(title="EduStream Analytics Service", version="1.0.0")

student_completion: dict[str, float] = {"STU-001:COURSE-DEMO": 0.2, "STU-002:COURSE-DEMO": 0.4}
student_lesson_counts: dict[str, int] = {"STU-001:COURSE-DEMO": 1, "STU-002:COURSE-DEMO": 2}
course_completion_samples: dict[str, list[float]] = {"COURSE-DEMO": [0.2, 0.4, 0.7, 0.9]}
course_quiz_scores: dict[str, list[float]] = {"COURSE-DEMO": [78.0, 82.0, 88.0]}
course_webinar_attendance: dict[str, list[float]] = {"COURSE-DEMO": [0.65, 0.8, 0.75]}
recommendation_scores: list[float] = [82.0, 85.0]
video_start_samples: list[float] = [2.1, 2.4, 2.7]


class CompletionIngestRequest(BaseModel):
    user_id: str
    course_id: str
    completion_ratio: float = Field(ge=0, le=1)
    completed_lessons: int = Field(ge=0)


class QuizIngestRequest(BaseModel):
    course_id: str
    score_pct: float = Field(ge=0, le=100)


class WebinarIngestRequest(BaseModel):
    course_id: str
    attendance_ratio: float = Field(ge=0, le=1)


class RecommendationAccuracyRequest(BaseModel):
    recommended_ids: list[str] = Field(default_factory=list)
    consumed_ids: list[str] = Field(default_factory=list)


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot {action}")


def _course_metrics(course_id: str) -> dict[str, float]:
    avg_completion = mean(course_completion_samples.get(course_id, [0.0]))
    avg_quiz = mean(course_quiz_scores.get(course_id, [0.0]))
    avg_attendance = mean(course_webinar_attendance.get(course_id, [0.0]))
    effectiveness = course_effectiveness(avg_completion, avg_quiz, avg_attendance)
    return {
        "avg_completion_ratio": round(avg_completion, 2),
        "avg_quiz_score": round(avg_quiz, 2),
        "avg_webinar_attendance": round(avg_attendance, 2),
        "course_effectiveness": effectiveness,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/analytics/ingest/completion")
async def ingest_completion(request: CompletionIngestRequest) -> dict[str, Any]:
    key = f"{request.user_id}:{request.course_id}"
    student_completion[key] = request.completion_ratio
    student_lesson_counts[key] = request.completed_lessons
    course_completion_samples.setdefault(request.course_id, []).append(request.completion_ratio)
    return {"status": "accepted", "key": key}


@app.post("/analytics/ingest/quiz")
async def ingest_quiz(request: QuizIngestRequest) -> dict[str, Any]:
    course_quiz_scores.setdefault(request.course_id, []).append(request.score_pct)
    return {"status": "accepted", "course_id": request.course_id}


@app.post("/analytics/ingest/webinar")
async def ingest_webinar(request: WebinarIngestRequest) -> dict[str, Any]:
    course_webinar_attendance.setdefault(request.course_id, []).append(request.attendance_ratio)
    return {"status": "accepted", "course_id": request.course_id}


@app.post("/analytics/recommendation-accuracy")
async def ingest_recommendation_accuracy(request: RecommendationAccuracyRequest) -> dict[str, float]:
    score = recommendation_accuracy(request.recommended_ids, request.consumed_ids)
    recommendation_scores.append(score)
    return {"accuracy_pct": score}


@app.get("/analytics/student/{user_id}")
async def student_metrics(user_id: str, course_id: str = "COURSE-DEMO") -> dict[str, Any]:
    key = f"{user_id}:{course_id}"
    completion_ratio = student_completion.get(key, 0.0)
    risk = dropout_risk(completion_ratio, missed_deadlines=1, webinar_attendance_ratio=0.75)
    return {
        "user_id": user_id,
        "course_id": course_id,
        "completion_ratio": completion_ratio,
        "completed_lessons": student_lesson_counts.get(key, 0),
        "dropout_risk": risk,
    }


@app.get("/analytics/course/{course_id}")
async def course_metrics(course_id: str, actor_role: Role = Role.INSTRUCTOR) -> dict[str, Any]:
    _assert_permission(actor_role, "analytics:read")
    metrics = _course_metrics(course_id)
    metrics["course_id"] = course_id
    return metrics


@app.get("/analytics/kpi")
async def kpi() -> dict[str, Any]:
    estimated_video_start = estimate_video_start_seconds(cdn_cache_hit_ratio=0.82, average_segment_size_mb=2.1)
    recommendation = round(mean(recommendation_scores), 2) if recommendation_scores else 0.0
    return {
        "video_load_seconds_estimate": estimated_video_start,
        "recommendation_accuracy_pct": recommendation,
        "target_video_load_seconds": settings.video_load_target_seconds,
        "target_recommendation_accuracy_pct": settings.recommendation_accuracy_target,
        "capacity_target_viewers": settings.webinar_viewers_target,
    }


@app.get("/dashboards/{role}")
async def dashboard(role: Role) -> dict[str, Any]:
    course_metrics = _course_metrics("COURSE-DEMO")
    widgets = {
        Role.STUDENT: ["progress", "deadlines", "recommended_lessons", "webinar_reminders"],
        Role.INSTRUCTOR: ["course_effectiveness", "quiz_performance", "attendance", "dropout_risk"],
        Role.ADMIN: ["platform_kpi", "institution_breakdown", "audit_health", "capacity"],
        Role.MODERATOR: ["webinar_quality", "chat_activity", "incident_feed", "notifications"],
    }
    return {"role": role.value, "widgets": widgets[role], "course_metrics": course_metrics}
