from __future__ import annotations

from statistics import mean
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.edustream_common import (
    QuestionType,
    Quiz,
    QuizCreateRequest,
    QuizQuestion,
    QuizSubmission,
    QuizSubmissionRequest,
    Role,
    Settings,
    grade_essay,
    has_permission,
    parallel_grading_hint,
    quiz_score,
)

settings = Settings(service_name="test-service", service_port=8303)
app = FastAPI(title="EduStream Test Service", version="1.0.0")


def _seed_demo_quiz() -> Quiz:
    questions = [
        QuizQuestion(
            question_id="Q-1",
            prompt="Which slide should open the story?",
            question_type=QuestionType.SINGLE_CHOICE,
            options=["Raw table", "Executive summary", "Appendix"],
            correct_answers=["Executive summary"],
            max_points=1,
        ),
        QuizQuestion(
            question_id="Q-2",
            prompt="Select signals of a strong narrative.",
            question_type=QuestionType.MULTIPLE_CHOICE,
            options=["clear tension", "random metrics", "single call to action"],
            correct_answers=["clear tension", "single call to action"],
            max_points=2,
        ),
        QuizQuestion(
            question_id="Q-3",
            prompt="Briefly explain why audience context matters.",
            question_type=QuestionType.ESSAY,
            correct_answers=["audience", "decision", "context"],
            max_points=3,
        ),
    ]
    return Quiz(
        quiz_id="QUIZ-DEMO",
        course_id="COURSE-DEMO",
        lesson_id="LESSON-3",
        title="Insight Prioritization Quiz",
        questions=questions,
    )


quizzes: dict[str, Quiz] = {"QUIZ-DEMO": _seed_demo_quiz()}
submissions: dict[str, QuizSubmission] = {}
quiz_score_history: dict[str, list[float]] = {"QUIZ-DEMO": [75.0, 88.0, 91.0]}


class EssayGradeRequest(BaseModel):
    text: str
    keywords: list[str] = Field(default_factory=list)
    actor_role: Role


class GradingPlanRequest(BaseModel):
    submission_count: int = Field(ge=0)
    institutions: int = Field(ge=1)
    actor_role: Role


EssayGradeRequest.model_rebuild()
GradingPlanRequest.model_rebuild()


def _assert_create(role: Role) -> None:
    if not has_permission(role, "quiz:create"):
        raise HTTPException(status_code=403, detail="Forbidden")


def _normalize_answer(answer: object) -> list[str]:
    if isinstance(answer, list):
        return [str(item) for item in answer]
    if answer is None:
        return []
    return [str(answer)]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/quizzes")
async def create_quiz(request: QuizCreateRequest) -> dict:
    _assert_create(request.actor_role)
    quiz = Quiz(
        quiz_id=str(uuid4()),
        course_id=request.course_id,
        lesson_id=request.lesson_id,
        title=request.title,
        questions=request.questions,
    )
    quizzes[quiz.quiz_id] = quiz
    quiz_score_history[quiz.quiz_id] = []
    return quiz.model_dump(mode="json")


@app.get("/quizzes")
async def list_quizzes(course_id: str | None = None) -> dict:
    items = []
    for quiz in quizzes.values():
        if course_id and quiz.course_id != course_id:
            continue
        items.append(quiz.model_dump(mode="json"))
    return {"items": items}


@app.get("/quizzes/{quiz_id}")
async def get_quiz(quiz_id: str) -> dict:
    quiz = quizzes.get(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return quiz.model_dump(mode="json")


@app.post("/submissions")
async def submit_quiz(request: QuizSubmissionRequest) -> dict:
    if request.actor_role not in {Role.STUDENT, Role.INSTRUCTOR, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    quiz = quizzes.get(request.quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    feedback: dict[str, dict] = {}
    scored_points = 0.0
    total_points = sum(question.max_points for question in quiz.questions)

    for question in quiz.questions:
        answer = request.answers.get(question.question_id)
        if question.question_type in {QuestionType.SINGLE_CHOICE, QuestionType.MULTIPLE_CHOICE, QuestionType.TEXT}:
            normalized = _normalize_answer(answer)
            correct = set(normalized) == set(question.correct_answers)
            scored_points += question.max_points if correct else 0
            feedback[question.question_id] = {"correct": correct, "expected": question.correct_answers}
        else:
            essay = grade_essay(str(answer or ""), question.correct_answers)
            question_points = round((float(essay["score_pct"]) / 100) * question.max_points, 2)
            scored_points += question_points
            feedback[question.question_id] = essay

    score_pct = quiz_score(scored_points, total_points)
    submission = QuizSubmission(
        submission_id=str(uuid4()),
        quiz_id=quiz.quiz_id,
        user_id=request.user_id,
        score_pct=score_pct,
        passed=score_pct >= 60,
        feedback=feedback,
    )
    submissions[submission.submission_id] = submission
    quiz_score_history.setdefault(quiz.quiz_id, []).append(score_pct)
    return submission.model_dump(mode="json")


@app.get("/submissions/{submission_id}")
async def get_submission(submission_id: str) -> dict:
    submission = submissions.get(submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Submission not found")
    return submission.model_dump(mode="json")


@app.post("/essays/grade")
async def evaluate_essay(request: EssayGradeRequest) -> dict:
    if request.actor_role not in {Role.INSTRUCTOR, Role.ADMIN, Role.STUDENT}:
        raise HTTPException(status_code=403, detail="Forbidden")
    return grade_essay(request.text, request.keywords)


@app.post("/grading/parallel-plan")
async def grading_plan(request: GradingPlanRequest) -> dict:
    if request.actor_role not in {Role.INSTRUCTOR, Role.ADMIN}:
        raise HTTPException(status_code=403, detail="Forbidden")
    return parallel_grading_hint(request.submission_count, request.institutions)


@app.get("/analytics/quiz/{quiz_id}")
async def quiz_analytics(quiz_id: str) -> dict:
    history = quiz_score_history.get(quiz_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return {"quiz_id": quiz_id, "avg_score_pct": round(mean(history), 2) if history else 0.0, "attempts": len(history)}
