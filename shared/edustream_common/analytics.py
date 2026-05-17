from __future__ import annotations


def recommendation_accuracy(recommended_ids: list[str], consumed_ids: list[str]) -> float:
    if not recommended_ids:
        return 0.0
    recommended = set(recommended_ids)
    consumed = set(consumed_ids)
    if not consumed:
        return 0.0
    return round((len(recommended & consumed) / len(recommended)) * 100, 2)


def dropout_risk(completion_ratio: float, missed_deadlines: int, webinar_attendance_ratio: float) -> float:
    score = (
        (1 - completion_ratio) * 0.55
        + min(missed_deadlines / 10, 1.0) * 0.25
        + (1 - webinar_attendance_ratio) * 0.2
    )
    return round(min(max(score, 0.0), 1.0), 2)


def quiz_score(correct_points: float, total_points: float) -> float:
    if total_points <= 0:
        return 0.0
    return round((correct_points / total_points) * 100, 2)


def estimate_video_start_seconds(cdn_cache_hit_ratio: float, average_segment_size_mb: float) -> float:
    base = 4.5 - min(max(cdn_cache_hit_ratio, 0.0), 1.0) * 2.4
    payload_penalty = max(0.0, average_segment_size_mb - 2.0) * 0.2
    return round(max(0.8, base + payload_penalty), 2)


def parallel_grading_hint(submission_count: int, institutions: int) -> dict[str, int]:
    workers = min(24, max(1, institutions * 2, submission_count // 40))
    chunk_size = max(10, submission_count // max(workers, 1)) if submission_count else 10
    return {"workers": workers, "chunk_size": chunk_size, "submissions": submission_count}


def course_effectiveness(avg_completion_ratio: float, avg_quiz_score: float, webinar_attendance_ratio: float) -> float:
    score = avg_completion_ratio * 45 + (avg_quiz_score / 100) * 35 + webinar_attendance_ratio * 20
    return round(score, 2)
