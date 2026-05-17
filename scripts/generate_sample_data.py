from __future__ import annotations

import json
import random
from pathlib import Path

OUTPUT = Path(__file__).resolve().parents[1] / "data" / "samples" / "learning_events.json"

FORMATS = ["video_lecture", "text_material", "quiz", "webinar", "project_work"]
LANGUAGES = ["ru", "en", "kk"]
TOPICS = ["analytics", "storytelling", "python", "sql", "product", "design"]


def main() -> None:
    random.seed(42)
    institutions = [f"UNI-{idx:03d}" for idx in range(1, 31)]
    records: list[dict] = []

    for idx in range(1, 12001):
        records.append(
            {
                "event_id": f"EVT-{idx:05d}",
                "course_id": f"COURSE-{random.randint(1, 800):04d}",
                "user_id": f"STU-{random.randint(1, 5000):05d}",
                "institution_id": random.choice(institutions),
                "language": random.choice(LANGUAGES),
                "format": random.choice(FORMATS),
                "topic": random.choice(TOPICS),
                "completion_ratio": round(random.uniform(0.05, 1.0), 2),
                "quiz_score": round(random.uniform(35, 100), 2),
                "webinar_attendance_ratio": round(random.uniform(0.2, 1.0), 2),
            }
        )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

    print(f"Generated {len(records)} records -> {OUTPUT}")


if __name__ == "__main__":
    main()
