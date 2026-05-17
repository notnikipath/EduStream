from locust import HttpUser, between, task


class GatewayUser(HttpUser):
    wait_time = between(1, 2)

    @task(3)
    def health(self) -> None:
        self.client.get("/health")

    @task(2)
    def service_health(self) -> None:
        self.client.get("/services/health")

    @task(1)
    def complete_lesson(self) -> None:
        self.client.post(
            "/workflow/complete-lesson",
            json={
                "user_id": "STU-LOAD",
                "course_id": "COURSE-DEMO",
                "lesson_id": "LESSON-1",
                "actor_role": "student",
            },
        )
