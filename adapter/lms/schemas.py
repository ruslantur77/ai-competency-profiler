from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class LmsSubmissionTest(BaseModel):
    test_case_id: int
    status: str
    time_ms: int
    actual_text: Optional[str] = None
    passed: bool


class LmsSubmission(BaseModel):
    submission_id: int
    language: str
    code: Optional[str] = None
    verdict: Optional[str] = None
    total_time_ms: Optional[int] = None
    created_at: datetime
    tests: list[LmsSubmissionTest] = []


class LmsCase(BaseModel):
    case_id: int
    title: str
    description: Optional[str] = None
    attempts_count: int
    last_submission_at: Optional[datetime] = None
    submissions: list[LmsSubmission] = []


class LmsLecture(BaseModel):
    lecture_id: int
    slug: str
    title: str
    progress_status: Optional[str] = None
    completed_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class LmsQuiz(BaseModel):
    lecture_id: int
    attempts_used: int
    attempts_left: int
    best_score: Optional[int] = None
    max_score: Optional[int] = None
    last_attempt_at: Optional[datetime] = None


class LmsExamAttempt(BaseModel):
    attempt_id: int
    attempt_number: int
    status: str
    score: Optional[int] = None
    max_score: Optional[int] = None
    started_at: datetime
    finished_at: Optional[datetime] = None


class LmsExam(BaseModel):
    exam_id: int
    name: str
    attempts_used: int
    attempts_left: int
    last_attempt_at: Optional[datetime] = None
    attempts: list[LmsExamAttempt] = []


class LmsUser(BaseModel):
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None


class LmsUserProgress(BaseModel):
    user: LmsUser
    cases: list[LmsCase] = []
    lectures: list[LmsLecture] = []
    quizzes: list[LmsQuiz] = []
    exams: list[LmsExam] = []