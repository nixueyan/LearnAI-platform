from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, Field, PlainSerializer

def _serialize_dt(dt: datetime) -> str:
    s = dt.isoformat()
    return s + 'Z' if dt.tzinfo is None else s

UtcDateTime = Annotated[datetime, PlainSerializer(_serialize_dt, return_type=str)]


class UserCreate(BaseModel):
    username: str
    password: str = Field(min_length=6, description="至少 6 位")


class UserOut(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """登录/注册成功后的响应：包含签名 token，前端用于后续请求鉴权。"""
    id: int
    username: str
    token: str


class ProfileBase(BaseModel):
    name: Optional[str] = None
    grade: Optional[str] = None
    major: Optional[str] = None
    interests: Optional[str] = None
    goal: Optional[str] = None


class ProfileOut(ProfileBase):
    id: int
    user_id: int
    ability_curve: Optional[str] = None
    created_at: UtcDateTime
    updated_at: UtcDateTime

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    name: str
    category: str = "理工"
    description: Optional[str] = None


class SubjectOut(BaseModel):
    id: int
    name: str
    category: str
    description: Optional[str] = None
    cover_image: Optional[str] = None

    class Config:
        from_attributes = True


class ChapterOut(BaseModel):
    id: int
    subject_id: int
    title: str
    order: int
    summary: Optional[str] = None

    class Config:
        from_attributes = True


class ResourceOut(BaseModel):
    id: int
    subject_id: int
    chapter_id: int
    title: str
    resource_type: str
    content: Optional[str] = None
    is_public: bool
    view_count: int = 0

    class Config:
        from_attributes = True


class SubsectionCreate(BaseModel):
    title: str
    content: Optional[str] = None
    order: Optional[int] = 0
    is_published: Optional[bool] = True


class SubsectionOut(BaseModel):
    id: int
    chapter_id: int
    title: str
    content: Optional[str] = None
    order: int
    is_published: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime

    class Config:
        from_attributes = True


class SubsectionProgressCreate(BaseModel):
    user_id: int
    status: str


class SubsectionProgressOut(BaseModel):
    id: int
    user_id: int
    subsection_id: int
    status: str
    updated_at: UtcDateTime

    class Config:
        from_attributes = True


class NoteCreate(BaseModel):
    chapter_id: int
    title: Optional[str] = None
    content: Optional[str] = None


class NoteOut(NoteCreate):
    id: int
    user_id: int
    updated_at: UtcDateTime
    created_at: UtcDateTime

    class Config:
        from_attributes = True


class QuizRequest(BaseModel):
    chapter_id: int
    question_types: List[str] = []
    difficulty: str = ""
    count: int = 10
    question_ids: List[int] | None = None   # 错题重练时指定具体题目


class ResourceGenerateRequest(BaseModel):
    resource_types: List[str]   # e.g. ["讲解文档", "思维导图"]
    provider: str = "xunfei"   # 由前端选择，不再写死


class QuestionOut(BaseModel):
    id: int
    chapter_id: int
    question_type: str
    difficulty: str
    content: str
    options: Optional[str] = None      # JSON string, 前端自行解析
    answer: str                        # 生成时不返回，提交后可用于展示
    explanation: Optional[str] = None
    created_at: UtcDateTime

    class Config:
        from_attributes = True


class QuizSubmit(BaseModel):
    chapter_id: int
    question_ids: List[int]
    answers: List[str]


class QuizRecordOut(BaseModel):
    id: int
    user_id: int
    chapter_id: int
    score: int
    total_questions: int
    wrong_items: Optional[str] = None
    created_at: UtcDateTime

    class Config:
        from_attributes = True


class AIChatRequest(BaseModel):
    user_id: int
    subject_id: Optional[int] = None
    chapter_id: Optional[int] = None
    provider: str = "xunfei"
    agent_role: str = "tutor"    # tutor / profile / path
    prompt: str


class AIChatResponse(BaseModel):
    answer: str


class ProgressUpdate(BaseModel):
    chapter_id: int
    status: str


class ProgressOut(BaseModel):
    id: int
    user_id: int
    chapter_id: int
    status: str
    updated_at: UtcDateTime

    class Config:
        from_attributes = True
