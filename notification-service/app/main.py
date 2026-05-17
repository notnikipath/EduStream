from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.edustream_common import NotificationChannel, Role, Settings, has_permission

settings = Settings(service_name="notification-service", service_port=8307)
app = FastAPI(title="EduStream Notification Service", version="1.0.0")

messages: list[dict[str, Any]] = []


class NotificationRequest(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    actor_role: Role


class WebinarReminderRequest(BaseModel):
    webinar_id: str
    course_id: str
    recipient: str
    starts_at: str
    actor_role: Role


class CertificateNotificationRequest(BaseModel):
    user_id: str
    certificate_url: str
    actor_role: Role


NotificationRequest.model_rebuild()
WebinarReminderRequest.model_rebuild()
CertificateNotificationRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(request: NotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = request.model_dump(mode="json")
    payload["status"] = "queued"
    messages.append(payload)
    return payload


@app.post("/notify/webinar-reminder")
async def webinar_reminder(request: WebinarReminderRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = {
        "channel": NotificationChannel.PUSH.value,
        "recipient": request.recipient,
        "subject": f"Webinar {request.webinar_id} starts soon",
        "body": f"Your webinar for course {request.course_id} starts at {request.starts_at}.",
        "status": "queued",
    }
    messages.append(payload)
    return payload


@app.post("/notify/certificate")
async def certificate_notification(request: CertificateNotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = {
        "channel": NotificationChannel.EMAIL.value,
        "recipient": request.user_id,
        "subject": "Your EduStream certificate is ready",
        "body": f"Certificate download: {request.certificate_url}",
        "status": "queued",
    }
    messages.append(payload)
    return payload


@app.get("/notify/history")
async def notification_history() -> dict[str, Any]:
    return {"items": messages, "count": len(messages)}
