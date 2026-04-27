from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# --- Справочник курсов ---

class LmsCourseListItem(BaseModel):
    """GET /integration/courses — элемент списка."""
    course_id: int
    title: str


class LmsCaseRef(BaseModel):
    """Задача внутри GET /integration/courses/{course_id}."""
    case_id: int
    title: str
    description: Optional[str] = None
    difficulty: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    tests_count: int = 0


class LmsQuizRef(BaseModel):
    """Квиз внутри GET /integration/courses/{course_id}."""
    lecture_id: int
    slug: str
    title: str
    description: Optional[str] = None
    is_published: bool = False
    quiz_max_attempts: Optional[int] = None
    questions_count: int = 0
    estimated_minutes: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class LmsCourseDetail(BaseModel):
    """GET /integration/courses/{course_id} — детальная информация."""
    course_id: int
    title: str
    slug: str
    description: Optional[str] = None
    status: str
    visibility: Optional[str] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    cases: list[LmsCaseRef] = []
    quizzes: list[LmsQuizRef] = []
    exams: list = []


# --- Прогресс пользователей ---

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


class LmsCaseProgress(BaseModel):
    """Прогресс по code-задаче из /users/progress."""
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
    cases: list[LmsCaseProgress] = []
    lectures: list[LmsLecture] = []
    quizzes: list[LmsQuiz] = []
    exams: list[LmsExam] = []

class LmsQuizOption(BaseModel):
    option_id: int
    text: str
    is_correct: bool
    position: int


class LmsQuizQuestion(BaseModel):
    question_id: int
    text: str
    explanation: Optional[str] = None
    position: int
    irt_a: Optional[float] = None
    irt_d: Optional[float] = None
    irt_c: Optional[float] = None
    concept_id: Optional[str] = None
    options: list[LmsQuizOption] = []


class LmsQuizDetail(BaseModel):
    """GET /integration/lectures/{slug}/quiz"""
    lecture_id: int
    lecture_slug: str
    course_id: int
    lecture_title: str
    is_published: bool
    max_attempts: Optional[int] = None
    total_questions: int = 0
    questions: list[LmsQuizQuestion] = []    