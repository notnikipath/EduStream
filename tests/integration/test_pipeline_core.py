from pathlib import Path

from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

course_module = load_module("course_module", ROOT / "course-service" / "app" / "main.py")
learning_module = load_module("learning_module", ROOT / "learning-service" / "app" / "main.py")
test_module = load_module("test_module", ROOT / "test-service" / "app" / "main.py")
gamification_module = load_module("gamification_module", ROOT / "gamification-service" / "app" / "main.py")
analytics_module = load_module("analytics_module", ROOT / "analytics-service" / "app" / "main.py")
notification_module = load_module("notification_module", ROOT / "notification-service" / "app" / "main.py")
webinar_module = load_module("webinar_module", ROOT / "webinar-service" / "app" / "main.py")

course_client = TestClient(course_module.app)
learning_client = TestClient(learning_module.app)
test_client = TestClient(test_module.app)
gamification_client = TestClient(gamification_module.app)
analytics_client = TestClient(analytics_module.app)
notification_client = TestClient(notification_module.app)
webinar_client = TestClient(webinar_module.app)


def test_course_and_learning_dashboard_flow() -> None:
    course_response = course_client.get("/courses/COURSE-DEMO")
    assert course_response.status_code == 200
    course = course_response.json()
    assert course["title"] == "Data Storytelling Bootcamp"

    completion = learning_client.post(
        "/progress/complete-lesson",
        json={
            "user_id": "STU-001",
            "course_id": "COURSE-DEMO",
            "lesson_id": "LESSON-2",
            "actor_role": "student",
        },
    )
    assert completion.status_code == 200
    progress = completion.json()
    assert progress["completion_ratio"] >= 0.4

    analytics = analytics_client.post(
        "/analytics/ingest/completion",
        json={
            "user_id": "STU-001",
            "course_id": "COURSE-DEMO",
            "completion_ratio": progress["completion_ratio"],
            "completed_lessons": len(progress["completed_lessons"]),
        },
    )
    assert analytics.status_code == 200

    dashboard = learning_client.get("/dashboard/STU-001/COURSE-DEMO")
    assert dashboard.status_code == 200
    body = dashboard.json()
    assert body["progress"]["completion_ratio"] >= 0.4
    assert "recommended_lesson_ids" in body["recommendations"]


def test_quiz_reward_and_certificate_flow() -> None:
    submission = test_client.post(
        "/submissions",
        json={
            "quiz_id": "QUIZ-DEMO",
            "user_id": "STU-009",
            "answers": {
                "Q-1": "Executive summary",
                "Q-2": ["clear tension", "single call to action"],
                "Q-3": "Audience context matters because a decision maker needs context before taking action.",
            },
            "actor_role": "student",
        },
    )
    assert submission.status_code == 200
    payload = submission.json()
    assert payload["score_pct"] >= 60

    reward = gamification_client.post(
        "/points/add",
        json={
            "user_id": "STU-009",
            "course_id": "COURSE-DEMO",
            "points": 70,
            "reason": "Quiz QUIZ-DEMO submitted",
            "actor_id": "SYSTEM",
            "actor_role": "admin",
        },
    )
    assert reward.status_code == 200
    assert reward.json()["profile"]["total_points"] >= 70

    cert = gamification_client.post(
        "/certificates/issue",
        json={
            "user_id": "STU-009",
            "course_id": "COURSE-DEMO",
            "course_title": "Data Storytelling Bootcamp",
            "actor_id": "SYSTEM",
            "actor_role": "admin",
        },
    )
    assert cert.status_code == 200

    notice = notification_client.post(
        "/notify/certificate",
        json={
            "user_id": "STU-009",
            "certificate_url": cert.json()["url"],
            "actor_role": "admin",
        },
    )
    assert notice.status_code == 200


def test_webinar_join_and_publish_flow() -> None:
    join = webinar_client.post(
        "/webinars/WEB-DEMO/join",
        json={"user_id": "STU-010", "actor_role": "student"},
    )
    assert join.status_code == 200
    assert "STU-010" in join.json()["attendees"]

    publish = webinar_client.post(
        "/integrations/youtube/publish",
        json={
            "actor_id": "INST-001",
            "actor_role": "instructor",
            "webinar_id": "WEB-DEMO",
            "youtube_url": "https://youtube.example.com/watch?v=demo",
        },
    )
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"
