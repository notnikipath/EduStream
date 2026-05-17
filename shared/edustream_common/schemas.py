from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ContentFormat(str, Enum):
    VIDEO_LECTURE = "video_lecture"
    WEBINAR = "webinar"
    TEXT_MATERIAL = "text_material"
    QUIZ = "quiz"
    ASSIGNMENT = "assignment"
    PROJECT_WORK = "project_work"


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class QuestionType(str, Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    ESSAY = "essay"


class WebinarStatus(str, Enum):
    SCHEDULED = "scheduled"
    LIVE = "live"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AchievementTier(str, Enum):
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    PUSH = "push"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"


class Role(str, Enum):
    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"
    MODERATOR = "moderator"


class MaterialAsset(BaseModel):
    asset_id: str
    filename: str
    content_type: str
    url: str
    size_bytes: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Lesson(BaseModel):
    lesson_id: str
    title: str
    format: ContentFormat
    duration_minutes: int = Field(gt=0)
    difficulty: Difficulty = Difficulty.BEGINNER
    tags: list[str] = Field(default_factory=list)
    order: int = Field(ge=1)
    asset: MaterialAsset | None = None


class CourseModule(BaseModel):
    module_id: str
    title: str
    summary: str = ""
    lessons: list[Lesson] = Field(default_factory=list)


class CourseCreateRequest(BaseModel):
    title: str
    description: str
    instructor_id: str
    language: str = Field(default="ru", pattern="^(ru|en)$")
    institution_id: str | None = None
    formats: list[ContentFormat] = Field(default_factory=lambda: [ContentFormat.VIDEO_LECTURE])
    difficulty: Difficulty = Difficulty.BEGINNER
    actor_role: Role


class Course(BaseModel):
    course_id: str
    title: str
    description: str
    instructor_id: str
    language: str
    institution_id: str | None = None
    formats: list[ContentFormat]
    difficulty: Difficulty
    modules: list[CourseModule] = Field(default_factory=list)
    published: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EnrollmentRequest(BaseModel):
    user_id: str
    course_id: str
    actor_role: Role


class Enrollment(BaseModel):
    enrollment_id: str
    user_id: str
    course_id: str
    enrolled_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    deadlines: dict[str, str] = Field(default_factory=dict)


class LessonCompletionRequest(BaseModel):
    user_id: str
    course_id: str
    lesson_id: str
    actor_role: Role


class CourseProgress(BaseModel):
    progress_id: str
    user_id: str
    course_id: str
    completed_lessons: list[str] = Field(default_factory=list)
    completion_ratio: float = Field(ge=0, le=1, default=0)
    missed_deadlines: int = Field(ge=0, default=0)
    webinar_attendance_ratio: float = Field(ge=0, le=1, default=0)
    course_completed: bool = False
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LearningComment(BaseModel):
    comment_id: str
    course_id: str
    lesson_id: str
    user_id: str
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QuizQuestion(BaseModel):
    question_id: str
    prompt: str
    question_type: QuestionType
    options: list[str] = Field(default_factory=list)
    correct_answers: list[str] = Field(default_factory=list)
    max_points: int = Field(default=1, ge=1)


class QuizCreateRequest(BaseModel):
    course_id: str
    lesson_id: str
    title: str
    questions: list[QuizQuestion] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class Quiz(BaseModel):
    quiz_id: str
    course_id: str
    lesson_id: str
    title: str
    questions: list[QuizQuestion]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class QuizSubmissionRequest(BaseModel):
    quiz_id: str
    user_id: str
    answers: dict[str, Any] = Field(default_factory=dict)
    actor_role: Role


class QuizSubmission(BaseModel):
    submission_id: str
    quiz_id: str
    user_id: str
    score_pct: float = Field(ge=0, le=100)
    passed: bool
    feedback: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class WebinarCreateRequest(BaseModel):
    course_id: str
    title: str
    scheduled_at: datetime
    host_id: str
    provider: str = "native"
    actor_role: Role


class Webinar(BaseModel):
    webinar_id: str
    course_id: str
    title: str
    scheduled_at: datetime
    host_id: str
    status: WebinarStatus = WebinarStatus.SCHEDULED
    provider: str = "native"
    attendees: list[str] = Field(default_factory=list)
    chat_enabled: bool = True
    recording_url: str | None = None
    polls: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Achievement(BaseModel):
    achievement_id: str
    user_id: str
    course_id: str
    title: str
    tier: AchievementTier
    description: str
    points_awarded: int = Field(ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Certificate(BaseModel):
    certificate_id: str
    user_id: str
    course_id: str
    course_title: str
    url: str
    issued_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class RecommendationRequest(BaseModel):
    user_id: str
    course_id: str
    completed_tags: list[str] = Field(default_factory=list)
    weak_topics: list[str] = Field(default_factory=list)
    actor_role: Role


class RecommendationResult(BaseModel):
    user_id: str
    course_id: str
    recommended_lesson_ids: list[str] = Field(default_factory=list)
    accuracy_hint: float = Field(ge=0, le=1, default=0.8)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationPayload(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CompletionWorkflowResult(BaseModel):
    progress: dict[str, Any]
    certificate: dict[str, Any] | None
    notification: dict[str, Any] | None
    analytics: dict[str, Any] | None
    completed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
