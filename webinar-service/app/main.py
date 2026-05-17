from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.edustream_common import (
    Role,
    Settings,
    Webinar,
    WebinarCreateRequest,
    WebinarStatus,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="webinar-service", service_port=8304)
app = FastAPI(title="EduStream Webinar Service", version="1.0.0")

webinars: dict[str, Webinar] = {}
chat_messages: dict[str, list[dict[str, Any]]] = {}
audit_log: list[dict[str, Any]] = []


class WebinarActionRequest(BaseModel):
    actor_id: str
    actor_role: Role


class JoinRequest(BaseModel):
    user_id: str
    actor_role: Role


class ChatMessageRequest(BaseModel):
    user_id: str
    actor_role: Role
    text: str = Field(min_length=1, max_length=1000)


class PollCreateRequest(BaseModel):
    actor_id: str
    actor_role: Role
    question: str
    options: list[str] = Field(default_factory=list)


class RecordingRequest(BaseModel):
    actor_id: str
    actor_role: Role
    recording_url: str


class ZoomImportRequest(BaseModel):
    course_id: str
    title: str
    scheduled_at: datetime
    host_id: str
    actor_role: Role
    zoom_meeting_id: str


class YoutubePublishRequest(BaseModel):
    actor_id: str
    actor_role: Role
    webinar_id: str
    youtube_url: str


WebinarActionRequest.model_rebuild()
JoinRequest.model_rebuild()
ChatMessageRequest.model_rebuild()
PollCreateRequest.model_rebuild()
RecordingRequest.model_rebuild()
ZoomImportRequest.model_rebuild()
YoutubePublishRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot {action}")


def _append_audit(
    actor_id: str,
    actor_role: Role,
    action: str,
    object_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="webinar",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _get_webinar(webinar_id: str) -> Webinar:
    webinar = webinars.get(webinar_id)
    if webinar is None:
        raise HTTPException(status_code=404, detail="Webinar not found")
    return webinar


def _seed_demo() -> None:
    webinar = Webinar(
        webinar_id="WEB-DEMO",
        course_id="COURSE-DEMO",
        title="Live Q&A: Data Storytelling Clinic",
        scheduled_at=datetime.now(UTC) + timedelta(days=1),
        host_id="INST-001",
        status=WebinarStatus.SCHEDULED,
        provider="native",
        attendees=["STU-001", "STU-002"],
        polls=[
            {
                "poll_id": "POLL-001",
                "question": "What topic needs more examples?",
                "options": ["Dashboards", "Narrative", "Data cleanup"],
            }
        ],
    )
    webinars[webinar.webinar_id] = webinar
    chat_messages[webinar.webinar_id] = [
        {
            "message_id": "CHAT-001",
            "user_id": "STU-001",
            "text": "Will the recording be published after class?",
            "created_at": datetime.now(UTC).isoformat(),
        }
    ]


_seed_demo()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/webinars")
async def create_webinar(request: WebinarCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:create")
    webinar = Webinar(
        webinar_id=str(uuid4()),
        course_id=request.course_id,
        title=request.title,
        scheduled_at=request.scheduled_at,
        host_id=request.host_id,
        provider=request.provider,
    )
    webinars[webinar.webinar_id] = webinar
    chat_messages[webinar.webinar_id] = []
    _append_audit(request.host_id, request.actor_role, "webinar.create", webinar.webinar_id)
    return webinar.model_dump(mode="json")


@app.get("/webinars")
async def list_webinars(course_id: str | None = None) -> dict[str, Any]:
    items = []
    for webinar in webinars.values():
        if course_id and webinar.course_id != course_id:
            continue
        items.append(webinar.model_dump(mode="json"))
    items.sort(key=lambda item: item["scheduled_at"])
    return {"items": items, "count": len(items)}


@app.get("/webinars/{webinar_id}")
async def get_webinar(webinar_id: str) -> dict[str, Any]:
    return _get_webinar(webinar_id).model_dump(mode="json")


@app.post("/webinars/{webinar_id}/start")
async def start_webinar(webinar_id: str, request: WebinarActionRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:manage")
    webinar = _get_webinar(webinar_id)
    webinar.status = WebinarStatus.LIVE
    _append_audit(request.actor_id, request.actor_role, "webinar.start", webinar_id)
    return webinar.model_dump(mode="json")


@app.post("/webinars/{webinar_id}/end")
async def end_webinar(webinar_id: str, request: WebinarActionRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:manage")
    webinar = _get_webinar(webinar_id)
    webinar.status = WebinarStatus.COMPLETED
    _append_audit(request.actor_id, request.actor_role, "webinar.end", webinar_id)
    return webinar.model_dump(mode="json")


@app.post("/webinars/{webinar_id}/join")
async def join_webinar(webinar_id: str, request: JoinRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:join")
    webinar = _get_webinar(webinar_id)
    if request.user_id not in webinar.attendees:
        webinar.attendees.append(request.user_id)
    _append_audit(request.user_id, request.actor_role, "webinar.join", webinar_id)
    return {"webinar_id": webinar_id, "attendees": webinar.attendees, "count": len(webinar.attendees)}


@app.post("/webinars/{webinar_id}/chat")
async def add_chat_message(webinar_id: str, request: ChatMessageRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:join")
    webinar = _get_webinar(webinar_id)
    if not webinar.chat_enabled:
        raise HTTPException(status_code=400, detail="Chat is disabled for this webinar")
    message = {
        "message_id": str(uuid4()),
        "user_id": request.user_id,
        "text": request.text,
        "created_at": datetime.now(UTC).isoformat(),
    }
    chat_messages.setdefault(webinar_id, []).append(message)
    return message


@app.post("/webinars/{webinar_id}/polls")
async def create_poll(webinar_id: str, request: PollCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:manage")
    webinar = _get_webinar(webinar_id)
    poll = {"poll_id": str(uuid4()), "question": request.question, "options": request.options}
    webinar.polls.append(poll)
    _append_audit(request.actor_id, request.actor_role, "webinar.poll.create", webinar_id, {"poll_id": poll["poll_id"]})
    return poll


@app.post("/webinars/{webinar_id}/recording")
async def attach_recording(webinar_id: str, request: RecordingRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:manage")
    webinar = _get_webinar(webinar_id)
    webinar.recording_url = request.recording_url
    _append_audit(request.actor_id, request.actor_role, "webinar.recording.attach", webinar_id)
    return webinar.model_dump(mode="json")


@app.post("/integrations/zoom/import")
async def import_zoom_webinar(request: ZoomImportRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:create")
    webinar = Webinar(
        webinar_id=f"ZOOM-{request.zoom_meeting_id}",
        course_id=request.course_id,
        title=request.title,
        scheduled_at=request.scheduled_at,
        host_id=request.host_id,
        provider="zoom",
    )
    webinars[webinar.webinar_id] = webinar
    chat_messages[webinar.webinar_id] = []
    _append_audit(request.host_id, request.actor_role, "webinar.zoom.import", webinar.webinar_id)
    return webinar.model_dump(mode="json")


@app.post("/integrations/youtube/publish")
async def publish_to_youtube(request: YoutubePublishRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "webinar:manage")
    webinar = _get_webinar(request.webinar_id)
    webinar.recording_url = request.youtube_url
    _append_audit(request.actor_id, request.actor_role, "webinar.youtube.publish", request.webinar_id)
    return {"webinar_id": webinar.webinar_id, "youtube_url": request.youtube_url, "status": "published"}


@app.get("/capacity")
async def capacity_plan(active_webinars: int = 1) -> dict[str, Any]:
    return {
        "target_viewers": settings.webinar_viewers_target,
        "active_webinars": active_webinars,
        "balanced_nodes": max(2, min(12, active_webinars * 2)),
        "viewers_per_node": max(1, settings.webinar_viewers_target // max(1, active_webinars * 2)),
    }


@app.get("/audit")
async def get_audit_log() -> dict[str, Any]:
    return {"items": audit_log, "count": len(audit_log)}
