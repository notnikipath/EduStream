from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.edustream_common import (
    CourseProgress,
    Enrollment,
    EnrollmentRequest,
    LearningComment,
    LessonCompletionRequest,
    RecommendationRequest,
    RecommendationResult,
    Role,
    Settings,
    build_audit_event,
    dropout_risk,
    has_permission,
    recommend_next_lessons,
)

settings = Settings(service_name="learning-service", service_port=8302)
app = FastAPI(title="EduStream Learning Service", version="1.0.0")

lesson_catalog: dict[str, list[dict]] = {
    "COURSE-DEMO": [
        {"lesson_id": "LESSON-1", "tags": ["storytelling", "analytics"], "difficulty": "beginner"},
        {"lesson_id": "LESSON-2", "tags": ["slides", "communication"], "difficulty": "beginner"},
        {"lesson_id": "LESSON-3", "tags": ["analytics", "decision-making"], "difficulty": "intermediate"},
        {"lesson_id": "LESSON-4", "tags": ["webinar", "presentation"], "difficulty": "intermediate"},
        {"lesson_id": "LESSON-5", "tags": ["project", "portfolio", "storytelling"], "difficulty": "advanced"},
    ]
}
course_totals = {"COURSE-DEMO": 5}
enrollments: dict[tuple[str, str], Enrollment] = {
    ("STU-001", "COURSE-DEMO"): Enrollment(enrollment_id="ENR-001", user_id="STU-001", course_id="COURSE-DEMO")
}
progresses: dict[tuple[str, str], CourseProgress] = {
    ("STU-001", "COURSE-DEMO"): CourseProgress(
        progress_id="PRG-001",
        user_id="STU-001",
        course_id="COURSE-DEMO",
        completed_lessons=["LESSON-1"],
        completion_ratio=0.2,
        webinar_attendance_ratio=0.5,
        course_completed=False,
        updated_at=datetime.now(UTC),
    )
}
comments: list[LearningComment] = [
    LearningComment(
        comment_id="CMT-001",
        course_id="COURSE-DEMO",
        lesson_id="LESSON-1",
        user_id="STU-001",
        text="Great pacing, could use one more practical example.",
    )
]
audit_log: list[dict] = []


class CommentCreateRequest(BaseModel):
    course_id: str
    lesson_id: str
    user_id: str
    text: str = Field(min_length=1)
    actor_role: Role


CommentCreateRequest.model_rebuild()


def _assert_read_own_or_staff(actor_role: Role, actor_id: str, user_id: str) -> None:
    if actor_role in {Role.INSTRUCTOR, Role.ADMIN, Role.MODERATOR}:
        return
    if actor_role == Role.STUDENT and actor_id == user_id:
        return
    raise HTTPException(status_code=403, detail="Forbidden")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="learning",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _default_progress(user_id: str, course_id: str) -> CourseProgress:
    return CourseProgress(progress_id=str(uuid4()), user_id=user_id, course_id=course_id, updated_at=datetime.now(UTC))


def _recommendation_payload(user_id: str, course_id: str, weak_topics: list[str] | None = None) -> RecommendationResult:
    progress = progresses.get((user_id, course_id), _default_progress(user_id, course_id))
    completed_set = set(progress.completed_lessons)
    completed_tags = [
        tag
        for lesson in lesson_catalog.get(course_id, [])
        if lesson["lesson_id"] in completed_set
        for tag in lesson.get("tags", [])
    ]
    candidates = [lesson for lesson in lesson_catalog.get(course_id, []) if lesson["lesson_id"] not in completed_set]
    recommended = recommend_next_lessons(completed_tags, weak_topics or ["analytics"], candidates)
    return RecommendationResult(
        user_id=user_id,
        course_id=course_id,
        recommended_lesson_ids=recommended,
        accuracy_hint=0.84,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/enrollments")
async def enroll(request: EnrollmentRequest) -> dict:
    if request.actor_role not in {Role.STUDENT, Role.INSTRUCTOR, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    key = (request.user_id, request.course_id)
    if key not in enrollments:
        enrollments[key] = Enrollment(enrollment_id=str(uuid4()), user_id=request.user_id, course_id=request.course_id)
    progresses.setdefault(key, _default_progress(request.user_id, request.course_id))
    _audit(request.user_id, request.actor_role, "learning.enroll", request.course_id)
    return enrollments[key].model_dump(mode="json")


@app.get("/enrollments")
async def list_enrollments(user_id: str | None = None) -> dict:
    items = []
    for enrollment in enrollments.values():
        if user_id and enrollment.user_id != user_id:
            continue
        items.append(enrollment.model_dump(mode="json"))
    return {"items": items}


@app.post("/progress/complete-lesson")
async def complete_lesson(request: LessonCompletionRequest) -> dict:
    if request.actor_role not in {Role.STUDENT, Role.INSTRUCTOR, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    key = (request.user_id, request.course_id)
    enrollments.setdefault(
        key,
        Enrollment(
            enrollment_id=str(uuid4()),
            user_id=request.user_id,
            course_id=request.course_id,
        ),
    )
    progress = progresses.setdefault(key, _default_progress(request.user_id, request.course_id))
    if request.lesson_id not in progress.completed_lessons:
        progress.completed_lessons.append(request.lesson_id)
    total_lessons = course_totals.get(request.course_id, max(len(lesson_catalog.get(request.course_id, [])), 1))
    progress.completion_ratio = round(min(len(progress.completed_lessons) / max(total_lessons, 1), 1.0), 2)
    progress.webinar_attendance_ratio = 0.8 if progress.completion_ratio >= 0.6 else 0.5
    progress.course_completed = len(progress.completed_lessons) >= total_lessons
    progress.updated_at = datetime.now(UTC)
    _audit(request.user_id, request.actor_role, "learning.complete_lesson", request.lesson_id)
    return progress.model_dump(mode="json")


@app.get("/progress/{user_id}/{course_id}")
async def get_progress(user_id: str, course_id: str, actor_id: str, actor_role: Role) -> dict:
    _assert_read_own_or_staff(actor_role, actor_id, user_id)
    progress = progresses.get((user_id, course_id))
    if progress is None:
        raise HTTPException(status_code=404, detail="Progress not found")
    return progress.model_dump(mode="json")


@app.post("/comments")
async def add_comment(request: CommentCreateRequest) -> dict:
    if request.actor_role not in {Role.STUDENT, Role.INSTRUCTOR, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    comment = LearningComment(
        comment_id=str(uuid4()),
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        user_id=request.user_id,
        text=request.text,
    )
    comments.append(comment)
    _audit(request.user_id, request.actor_role, "learning.comment_add", request.lesson_id)
    return comment.model_dump(mode="json")


@app.get("/comments/{course_id}")
async def list_comments(course_id: str) -> dict:
    return {"items": [comment.model_dump(mode="json") for comment in comments if comment.course_id == course_id]}


@app.post("/recommendations")
async def recommendations(request: RecommendationRequest) -> dict:
    if request.actor_role not in {Role.STUDENT, Role.INSTRUCTOR, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    result = _recommendation_payload(request.user_id, request.course_id, request.weak_topics)
    return result.model_dump(mode="json")


@app.get("/dropout-risk/{user_id}/{course_id}")
async def dropout_snapshot(user_id: str, course_id: str, actor_role: Role = Role.INSTRUCTOR) -> dict:
    if not has_permission(actor_role, "learning:read") and actor_role != Role.STUDENT:
        raise HTTPException(status_code=403, detail="Forbidden")
    progress = progresses.get((user_id, course_id), _default_progress(user_id, course_id))
    risk = dropout_risk(progress.completion_ratio, progress.missed_deadlines, progress.webinar_attendance_ratio)
    return {"user_id": user_id, "course_id": course_id, "dropout_risk": risk}


@app.get("/dashboard/{user_id}/{course_id}")
async def learner_dashboard(user_id: str, course_id: str) -> dict:
    progress = progresses.get((user_id, course_id), _default_progress(user_id, course_id))
    recommendation = _recommendation_payload(user_id, course_id)
    risk = dropout_risk(progress.completion_ratio, progress.missed_deadlines, progress.webinar_attendance_ratio)
    return {
        "user_id": user_id,
        "course_id": course_id,
        "progress": progress.model_dump(mode="json"),
        "recommendations": recommendation.model_dump(mode="json"),
        "dropout_risk": risk,
        "comments_count": len([item for item in comments if item.course_id == course_id]),
    }


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict:
    if not has_permission(actor_role, "audit:read"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return {"items": audit_log[-limit:]}
