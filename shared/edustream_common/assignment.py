from __future__ import annotations

from collections import Counter

from .schemas import AchievementTier


def recommend_next_lessons(
    completed_tags: list[str],
    weak_topics: list[str],
    candidates: list[dict],
) -> list[str]:
    if not candidates:
        return []
    completed_counter = Counter(completed_tags)
    weak_counter = Counter(weak_topics)
    scored: list[tuple[float, str]] = []
    for lesson in candidates:
        lesson_id = str(lesson.get("lesson_id"))
        tags = lesson.get("tags", [])
        novelty = sum(1 for tag in tags if completed_counter[tag] == 0) * 0.25
        weakness_boost = sum(weak_counter[tag] for tag in tags) * 0.4
        difficulty_penalty = 0.1 if lesson.get("difficulty") == "advanced" and weak_topics else 0.0
        score = novelty + weakness_boost - difficulty_penalty
        scored.append((score, lesson_id))
    scored.sort(reverse=True)
    return [lesson_id for _, lesson_id in scored[:3]]


def grade_essay(text: str, keywords: list[str]) -> dict[str, object]:
    if not text.strip():
        return {"score_pct": 0.0, "feedback": "Essay is empty.", "matched_keywords": []}
    lowered = text.lower()
    matched = [keyword for keyword in keywords if keyword.lower() in lowered]
    coverage = len(matched) / max(len(keywords), 1)
    structure_bonus = 0.15 if len(text.split()) >= 80 else 0.0
    score = min(100.0, round((coverage + structure_bonus) * 100, 2))
    feedback = "Strong topical coverage." if score >= 75 else "Expand the answer with more key concepts."
    return {"score_pct": score, "feedback": feedback, "matched_keywords": matched}


def achievement_tier(total_points: int) -> AchievementTier:
    if total_points >= 800:
        return AchievementTier.GOLD
    if total_points >= 400:
        return AchievementTier.SILVER
    return AchievementTier.BRONZE
