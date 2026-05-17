from shared.edustream_common import AchievementTier, achievement_tier, grade_essay, recommend_next_lessons


def test_recommend_next_lessons_prefers_weak_topics() -> None:
    result = recommend_next_lessons(
        completed_tags=["storytelling"],
        weak_topics=["analytics", "analytics"],
        candidates=[
            {"lesson_id": "L1", "tags": ["analytics"], "difficulty": "beginner"},
            {"lesson_id": "L2", "tags": ["communication"], "difficulty": "beginner"},
            {"lesson_id": "L3", "tags": ["analytics", "project"], "difficulty": "advanced"},
        ],
    )
    assert "L1" in result
    assert len(result) <= 3


def test_grade_essay_detects_keywords() -> None:
    report = grade_essay(
        "The audience context shapes the decision and explains why the message should change.",
        ["audience", "decision", "context"],
    )
    assert report["score_pct"] > 0
    assert "audience" in report["matched_keywords"]


def test_achievement_tier_thresholds() -> None:
    assert achievement_tier(120) == AchievementTier.BRONZE
    assert achievement_tier(500) == AchievementTier.SILVER
    assert achievement_tier(900) == AchievementTier.GOLD
