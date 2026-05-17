from __future__ import annotations

import asyncio

import httpx

GATEWAY_URL = "http://localhost:8380"


async def main() -> None:
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            f"{GATEWAY_URL}/workflow/complete-lesson",
            json={
                "user_id": "STU-001",
                "course_id": "COURSE-DEMO",
                "lesson_id": "LESSON-5",
                "actor_role": "student",
            },
        )
        response.raise_for_status()
        print(response.json())


if __name__ == "__main__":
    asyncio.run(main())
