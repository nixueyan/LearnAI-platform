from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, index=True, nullable=False)
    hashed_password = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False)
    notes = relationship("Note", back_populates="user")
    quiz_records = relationship("QuizRecord", back_populates="user")
    progress = relationship("UserProgress", back_populates="user")
    conversations = relationship("Conversation", back_populates="user")
    tokens = relationship("Token", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    name = Column(String(128), nullable=True)
    grade = Column(String(64), nullable=True)
    major = Column(String(128), nullable=True)
    interests = Column(String(256), nullable=True)
    goal = Column(String(256), nullable=True)
    ability_curve = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="profile")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=True)
    role = Column(String(64), default="assistant")
    prompt = Column(Text, nullable=True)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="conversations")


class Token(Base):
    __tablename__ = "tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String(256), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="tokens")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), unique=True, nullable=False)
    category = Column(String(64), nullable=False)
    description = Column(Text, nullable=True)
    cover_image = Column(String(256), nullable=True)

    chapters = relationship("Chapter", back_populates="subject")


class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(256), nullable=False)
    order = Column(Integer, nullable=False)
    summary = Column(Text, nullable=True)

    subject = relationship("Subject", back_populates="chapters")
    resources = relationship("Resource", back_populates="chapter")
    quiz_records = relationship("QuizRecord", back_populates="chapter")
    notes = relationship("Note", back_populates="chapter")
    progress = relationship("UserProgress", back_populates="chapter")
    subsections = relationship("Subsection", back_populates="chapter")
    questions = relationship("Question", back_populates="chapter")


class Resource(Base):
    __tablename__ = "resources"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    title = Column(String(256), nullable=False)
    resource_type = Column(String(64), nullable=False)
    content = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True)
    view_count = Column(Integer, default=0)
    fav_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="resources")


class QuizRecord(Base):
    __tablename__ = "quiz_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    score = Column(Integer, nullable=False)
    total_questions = Column(Integer, nullable=False)
    wrong_items = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="quiz_records")
    chapter = relationship("Chapter", back_populates="quiz_records")


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    title = Column(String(256), nullable=True)
    content = Column(Text, nullable=True)
    is_deleted = Column(Boolean, default=False)   # 软删除标记
    deleted_at = Column(DateTime, nullable=True)   # 删除时间
    updated_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="notes")
    chapter = relationship("Chapter", back_populates="notes")


class UserProgress(Base):
    __tablename__ = "user_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    status = Column(String(32), nullable=False, default="未开始")
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="progress")
    chapter = relationship("Chapter", back_populates="progress")


class Subsection(Base):
    __tablename__ = "subsections"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    title = Column(String(256), nullable=False)
    content = Column(Text, nullable=True)
    """Order can be something like 1.1, 1.2 etc stored as integer for simplicity"""
    order = Column(Integer, nullable=False, default=0)
    is_published = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="subsections")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), nullable=False)
    question_type = Column(String(32), nullable=False)      # 选择题, 填空题, 计算题, 证明题
    difficulty = Column(String(16), nullable=False)          # 简单, 中等, 困难
    content = Column(Text, nullable=False)                   # 题目正文
    options = Column(Text, nullable=True)                    # JSON 选项列表（选择题用）
    answer = Column(Text, nullable=False)                    # 正确答案
    explanation = Column(Text, nullable=True)                # 题目解析
    created_at = Column(DateTime, default=datetime.utcnow)

    chapter = relationship("Chapter", back_populates="questions")


class SubsectionProgress(Base):
    __tablename__ = "subsection_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subsection_id = Column(Integer, ForeignKey("subsections.id"), nullable=False)
    status = Column(String(32), nullable=False, default="未学")
    updated_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    # relation to subsection optional


class Checkin(Base):
    __tablename__ = "checkins"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    checkin_date = Column(String(16), nullable=False)      # "2024-06-24" 格式
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
