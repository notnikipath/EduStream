from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.edustream_common import (
    ContentFormat,
    Course,
    CourseCreateRequest,
    CourseModule,
    Difficulty,
    Lesson,
    MaterialAsset,
    Role,
    Settings,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="course-service", service_port=8301)
app = FastAPI(title="EduStream Course Service", version="1.0.0")


def _seed_demo_course() -> Course:
    lessons_module_1 = [
        Lesson(
            lesson_id="LESSON-1",
            title="Narrative Arc for Analysts",
            format=ContentFormat.VIDEO_LECTURE,
            duration_minutes=18,
            difficulty=Difficulty.BEGINNER,
            tags=["storytelling", "analytics"],
            order=1,
            asset=MaterialAsset(
                asset_id="ASSET-1",
                filename="narrative-arc.mp4",
                content_type="video/mp4",
                url="s3://edustream/demo/narrative-arc.mp4",
                size_bytes=120_000_000,
            ),
        ),
        Lesson(
            lesson_id="LESSON-2",
            title="Slide Structure Workshop",
            format=ContentFormat.TEXT_MATERIAL,
            duration_minutes=14,
            difficulty=Difficulty.BEGINNER,
            tags=["slides", "communication"],
            order=2,
        ),
    ]
    lessons_module_2 = [
        Lesson(
            lesson_id="LESSON-3",
            title="Quiz: Insight Prioritization",
            format=ContentFormat.QUIZ,
            duration_minutes=12,
            difficulty=Difficulty.INTERMEDIATE,
            tags=["analytics", "decision-making"],
            order=1,
        ),
        Lesson(
            lesson_id="LESSON-4",
            title="Live Webinar: Demo Day Rehearsal",
            format=ContentFormat.WEBINAR,
            duration_minutes=45,
            difficulty=Difficulty.INTERMEDIATE,
            tags=["webinar", "presentation"],
            order=2,
        ),
        Lesson(
            lesson_id="LESSON-5",
            title="Capstone Pitch Deck",
            format=ContentFormat.PROJECT_WORK,
            duration_minutes=90,
            difficulty=Difficulty.ADVANCED,
            tags=["project", "storytelling", "portfolio"],
            order=3,
        ),
    ]
    return Course(
        course_id="COURSE-DEMO",
        title="Data Storytelling Bootcamp",
        description="A blended course with lectures, a live webinar, testing, and a capstone project.",
        instructor_id="INST-001",
        language="ru",
        institution_id="UNI-001",
        formats=[
            ContentFormat.VIDEO_LECTURE,
            ContentFormat.TEXT_MATERIAL,
            ContentFormat.QUIZ,
            ContentFormat.WEBINAR,
            ContentFormat.PROJECT_WORK,
        ],
        difficulty=Difficulty.INTERMEDIATE,
        published=True,
        modules=[
            CourseModule(
                module_id="MOD-1",
                title="Foundations",
                summary="Build the narrative base.",
                lessons=lessons_module_1,
            ),
            CourseModule(
                module_id="MOD-2",
                title="Delivery",
                summary="Practice live delivery and capstone work.",
                lessons=lessons_module_2,
            ),
        ],
        created_at=datetime.now(UTC),
    )


templates = {
    "tpl-bootcamp": {"template_id": "tpl-bootcamp", "name": "Bootcamp", "modules": ["Foundations", "Practice"]},
    "tpl-webinar-series": {
        "template_id": "tpl-webinar-series",
        "name": "Webinar Series",
        "modules": ["Sessions", "Recap", "Assessment"],
    },
}
courses: dict[str, Course] = {"COURSE-DEMO": _seed_demo_course()}
audit_log: list[dict] = []


class ModuleCreateRequest(BaseModel):
    title: str
    summary: str = ""
    actor_id: str
    actor_role: Role


class LessonCreateRequest(BaseModel):
    module_id: str
    title: str
    format: ContentFormat
    duration_minutes: int = Field(gt=0)
    difficulty: Difficulty = Difficulty.BEGINNER
    tags: list[str] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class AssetBindRequest(BaseModel):
    module_id: str
    lesson_id: str
    filename: str
    content_type: str
    url: str
    size_bytes: int = Field(gt=0)
    actor_id: str
    actor_role: Role


ModuleCreateRequest.model_rebuild()
LessonCreateRequest.model_rebuild()
AssetBindRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="course",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _find_module(course: Course, module_id: str) -> CourseModule:
    for module in course.modules:
        if module.module_id == module_id:
            return module
    raise HTTPException(status_code=404, detail="Module not found")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/templates")
async def list_templates() -> dict:
    return {"items": list(templates.values())}


@app.post("/courses")
async def create_course(request: CourseCreateRequest) -> dict:
    _assert_permission(request.actor_role, "course:create")
    course = Course(
        course_id=str(uuid4()),
        title=request.title,
        description=request.description,
        instructor_id=request.instructor_id,
        language=request.language,
        institution_id=request.institution_id,
        formats=request.formats,
        difficulty=request.difficulty,
        modules=[],
        created_at=datetime.now(UTC),
    )
    courses[course.course_id] = course
    _audit(request.instructor_id, request.actor_role, "course.create", course.course_id)
    return course.model_dump(mode="json")


@app.get("/courses")
async def list_courses(language: str | None = None) -> dict:
    items = []
    for course in courses.values():
        if language and course.language != language:
            continue
        items.append(course.model_dump(mode="json"))
    return {"items": items}


@app.get("/courses/{course_id}")
async def get_course(course_id: str, actor_role: Role = Role.STUDENT) -> dict:
    _assert_permission(actor_role, "course:read")
    course = courses.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course.model_dump(mode="json")


@app.get("/courses/{course_id}/catalog")
async def course_catalog(course_id: str, actor_role: Role = Role.STUDENT) -> dict:
    _assert_permission(actor_role, "course:read")
    course = courses.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    lessons = [lesson.model_dump(mode="json") for module in course.modules for lesson in module.lessons]
    return {"course_id": course_id, "items": lessons}


@app.post("/courses/{course_id}/modules")
async def add_module(course_id: str, request: ModuleCreateRequest) -> dict:
    _assert_permission(request.actor_role, "course:update")
    course = courses.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    module = CourseModule(module_id=str(uuid4()), title=request.title, summary=request.summary, lessons=[])
    course.modules.append(module)
    _audit(request.actor_id, request.actor_role, "course.module_add", course_id, {"module_id": module.module_id})
    return module.model_dump(mode="json")


@app.post("/courses/{course_id}/lessons")
async def add_lesson(course_id: str, request: LessonCreateRequest) -> dict:
    _assert_permission(request.actor_role, "course:update")
    course = courses.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    module = _find_module(course, request.module_id)
    lesson = Lesson(
        lesson_id=str(uuid4()),
        title=request.title,
        format=request.format,
        duration_minutes=request.duration_minutes,
        difficulty=request.difficulty,
        tags=request.tags,
        order=len(module.lessons) + 1,
    )
    module.lessons.append(lesson)
    _audit(request.actor_id, request.actor_role, "course.lesson_add", course_id, {"lesson_id": lesson.lesson_id})
    return lesson.model_dump(mode="json")


@app.post("/courses/{course_id}/assets")
async def bind_asset(course_id: str, request: AssetBindRequest) -> dict:
    _assert_permission(request.actor_role, "course:update")
    course = courses.get(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    module = _find_module(course, request.module_id)
    for lesson in module.lessons:
        if lesson.lesson_id == request.lesson_id:
            lesson.asset = MaterialAsset(
                asset_id=str(uuid4()),
                filename=request.filename,
                content_type=request.content_type,
                url=request.url,
                size_bytes=request.size_bytes,
            )
            _audit(
                request.actor_id,
                request.actor_role,
                "course.asset_bind",
                course_id,
                {"lesson_id": lesson.lesson_id},
            )
            return lesson.model_dump(mode="json")
    raise HTTPException(status_code=404, detail="Lesson not found")


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
