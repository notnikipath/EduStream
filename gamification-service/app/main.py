from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.edustream_common import (
    Achievement,
    Certificate,
    Role,
    Settings,
    achievement_tier,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="gamification-service", service_port=8305)
app = FastAPI(title="EduStream Gamification Service", version="1.0.0")

profiles: dict[str, dict[str, Any]] = {}
achievements: dict[str, list[Achievement]] = {}
certificates: dict[str, list[Certificate]] = {}
audit_log: list[dict[str, Any]] = []


class PointsAddRequest(BaseModel):
    user_id: str
    course_id: str
    points: int = Field(gt=0)
    reason: str
    actor_id: str
    actor_role: Role


class CertificateIssueRequest(BaseModel):
    user_id: str
    course_id: str
    course_title: str
    actor_id: str
    actor_role: Role


PointsAddRequest.model_rebuild()
CertificateIssueRequest.model_rebuild()


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
            object_type="gamification",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _profile_key(user_id: str, course_id: str) -> str:
    return f"{user_id}:{course_id}"


def _ensure_profile(user_id: str, course_id: str) -> dict[str, Any]:
    key = _profile_key(user_id, course_id)
    if key not in profiles:
        profiles[key] = {
            "user_id": user_id,
            "course_id": course_id,
            "total_points": 0,
            "tier": achievement_tier(0).value,
        }
    achievements.setdefault(key, [])
    certificates.setdefault(key, [])
    return profiles[key]


def _seed_demo() -> None:
    profile = _ensure_profile("STU-001", "COURSE-DEMO")
    profile["total_points"] = 260
    profile["tier"] = achievement_tier(260).value
    achievements[_profile_key("STU-001", "COURSE-DEMO")] = [
        Achievement(
            achievement_id="ACH-001",
            user_id="STU-001",
            course_id="COURSE-DEMO",
            title="First lesson completed",
            tier=achievement_tier(260),
            description="The student completed the first content block.",
            points_awarded=80,
        )
    ]


_seed_demo()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/points/add")
async def add_points(request: PointsAddRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "gamification:manage")
    profile = _ensure_profile(request.user_id, request.course_id)
    profile["total_points"] += request.points
    profile["tier"] = achievement_tier(profile["total_points"]).value

    achievement = Achievement(
        achievement_id=str(uuid4()),
        user_id=request.user_id,
        course_id=request.course_id,
        title=request.reason,
        tier=achievement_tier(profile["total_points"]),
        description=f"Points added for {request.reason.lower()}",
        points_awarded=request.points,
    )
    achievements[_profile_key(request.user_id, request.course_id)].append(achievement)
    _append_audit(request.actor_id, request.actor_role, "gamification.points.add", achievement.achievement_id)
    return {
        "profile": profile,
        "achievement": achievement.model_dump(mode="json"),
    }


@app.post("/certificates/issue")
async def issue_certificate(request: CertificateIssueRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "gamification:manage")
    _ensure_profile(request.user_id, request.course_id)
    certificate = Certificate(
        certificate_id=str(uuid4()),
        user_id=request.user_id,
        course_id=request.course_id,
        course_title=request.course_title,
        url=f"https://cdn.edustream.local/certificates/{request.user_id}-{request.course_id}.pdf",
    )
    certificates[_profile_key(request.user_id, request.course_id)].append(certificate)
    _append_audit(request.actor_id, request.actor_role, "gamification.certificate.issue", certificate.certificate_id)
    return certificate.model_dump(mode="json")


@app.get("/leaderboard/{course_id}")
async def leaderboard(course_id: str) -> dict[str, Any]:
    items = [profile for profile in profiles.values() if profile["course_id"] == course_id]
    items.sort(key=lambda item: item["total_points"], reverse=True)
    return {"items": items, "count": len(items)}


@app.get("/profiles/{user_id}")
async def get_profiles(user_id: str) -> dict[str, Any]:
    items = [profile for profile in profiles.values() if profile["user_id"] == user_id]
    return {"items": items, "count": len(items)}


@app.get("/certificates/{user_id}")
async def get_certificates(user_id: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for key, values in certificates.items():
        if key.startswith(f"{user_id}:"):
            items.extend(item.model_dump(mode="json") for item in values)
    return {"items": items, "count": len(items)}


@app.get("/audit")
async def get_audit_log() -> dict[str, Any]:
    return {"items": audit_log, "count": len(audit_log)}
