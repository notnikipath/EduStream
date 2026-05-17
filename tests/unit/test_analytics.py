from shared.edustream_common import dropout_risk, parallel_grading_hint, quiz_score, recommendation_accuracy


def test_recommendation_accuracy() -> None:
    assert recommendation_accuracy(["L1", "L2", "L3"], ["L2", "L4"]) == 33.33


def test_dropout_risk_is_bounded() -> None:
    risk = dropout_risk(0.25, 3, 0.4)
    assert 0 <= risk <= 1


def test_parallel_grading_hint_has_workers() -> None:
    plan = parallel_grading_hint(320, 4)
    assert plan["workers"] >= 1
    assert plan["chunk_size"] >= 10


def test_quiz_score() -> None:
    assert quiz_score(8, 10) == 80.0
