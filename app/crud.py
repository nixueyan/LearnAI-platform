from datetime import datetime
from typing import List
import hashlib
import secrets

from sqlalchemy.orm import Session

from . import models, schemas


def get_password_hash(password: str) -> str:
    """加盐哈希：格式 salt$<salt>$<sha256(salt+password)>，避免彩虹表反查。"""
    salt = secrets.token_hex(8)
    h = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"salt${salt}${h}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False
    # 新账户：加盐格式
    if hashed_password.startswith("salt$"):
        try:
            _, salt, h = hashed_password.split("$", 2)
        except ValueError:
            return False
        return h == hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
    # 兼容历史裸 SHA256 账户（首次登录后可改为加盐：在登录成功处重新哈希即可）
    return hashed_password == hashlib.sha256(plain_password.encode("utf-8")).hexdigest()


def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    profile = models.Profile(user_id=db_user.id)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return db_user


def create_profile(db: Session, user_id: int, profile_data: schemas.ProfileBase):
    profile = db.query(models.Profile).filter(models.Profile.user_id == user_id).first()
    if not profile:
        profile = models.Profile(user_id=user_id, **profile_data.dict())
        db.add(profile)
    else:
        for field, value in profile_data.dict().items():
            setattr(profile, field, value)
        profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return profile


def get_subjects(db: Session):
    return db.query(models.Subject).order_by(models.Subject.id).all()


def get_subject(db: Session, subject_id: int):
    return db.query(models.Subject).filter(models.Subject.id == subject_id).first()


def get_chapters_by_subject(db: Session, subject_id: int):
    return db.query(models.Chapter).filter(models.Chapter.subject_id == subject_id).order_by(models.Chapter.order).all()


def delete_subject(db: Session, subject_id: int) -> bool:
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if not subject:
        return False
    # 删除关联的章节、资源、笔记、进度、答题记录
    chapters = db.query(models.Chapter).filter(models.Chapter.subject_id == subject_id).all()
    chapter_ids = [c.id for c in chapters]
    if chapter_ids:
        db.query(models.Resource).filter(models.Resource.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
        db.query(models.Note).filter(models.Note.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
        db.query(models.QuizRecord).filter(models.QuizRecord.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
        db.query(models.UserProgress).filter(models.UserProgress.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
        db.query(models.Subsection).filter(models.Subsection.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
        db.query(models.Question).filter(models.Question.chapter_id.in_(chapter_ids)).delete(synchronize_session=False)
        db.query(models.Chapter).filter(models.Chapter.subject_id == subject_id).delete(synchronize_session=False)
    db.delete(subject)
    db.commit()
    return True


def get_chapter(db: Session, chapter_id: int):
    return db.query(models.Chapter).filter(models.Chapter.id == chapter_id).first()


def get_resource_for_chapter(db: Session, chapter_id: int):
    return db.query(models.Resource).filter(models.Resource.chapter_id == chapter_id, models.Resource.is_public == True).all()


def get_subsections_by_chapter(db: Session, chapter_id: int):
    return db.query(models.Subsection).filter(models.Subsection.chapter_id == chapter_id).order_by(models.Subsection.order).all()


def create_subsection(db: Session, chapter_id: int, subsection_data: schemas.SubsectionCreate):
    sub = models.Subsection(chapter_id=chapter_id, title=subsection_data.title, content=subsection_data.content or "", order=subsection_data.order or 0, is_published=subsection_data.is_published)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def update_subsection(db: Session, subsection_id: int, subsection_data: schemas.SubsectionCreate):
    sub = db.query(models.Subsection).filter(models.Subsection.id == subsection_id).first()
    if not sub:
        return None
    sub.title = subsection_data.title
    sub.content = subsection_data.content
    sub.order = subsection_data.order or sub.order
    sub.is_published = subsection_data.is_published
    sub.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(sub)
    return sub


def delete_subsection(db: Session, subsection_id: int):
    sub = db.query(models.Subsection).filter(models.Subsection.id == subsection_id).first()
    if not sub:
        return False
    db.delete(sub)
    db.commit()
    return True


def set_subsection_progress(db: Session, user_id: int, subsection_id: int, status: str):
    prog = db.query(models.SubsectionProgress).filter(models.SubsectionProgress.user_id == user_id, models.SubsectionProgress.subsection_id == subsection_id).first()
    if not prog:
        prog = models.SubsectionProgress(user_id=user_id, subsection_id=subsection_id, status=status)
        db.add(prog)
    else:
        prog.status = status
        prog.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(prog)
    return prog


def get_subsection_progress(db: Session, user_id: int, subsection_id: int):
    return db.query(models.SubsectionProgress).filter(models.SubsectionProgress.user_id == user_id, models.SubsectionProgress.subsection_id == subsection_id).first()


def create_resource(db: Session, resource: models.Resource):
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def save_quiz_record(db: Session, user_id: int, chapter_id: int, score: int, total_questions: int, wrong_items: str):
    record = models.QuizRecord(
        user_id=user_id,
        chapter_id=chapter_id,
        score=score,
        total_questions=total_questions,
        wrong_items=wrong_items,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def save_conversation(db: Session, user_id: int, subject_id: int | None, chapter_id: int | None, prompt: str, response: str):
    conversation = models.Conversation(
        user_id=user_id,
        subject_id=subject_id,
        chapter_id=chapter_id,
        role="assistant",
        prompt=prompt,
        response=response,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def get_quiz_history(db: Session, user_id: int):
    return db.query(models.QuizRecord).filter(models.QuizRecord.user_id == user_id).order_by(models.QuizRecord.created_at.desc()).all()


def get_notes(db: Session, user_id: int, chapter_id: int = None, include_deleted: bool = False):
    query = db.query(models.Note).filter(models.Note.user_id == user_id)
    if include_deleted:
        query = query.filter(models.Note.is_deleted == True)  # 只看废纸篓
    else:
        query = query.filter(models.Note.is_deleted == False)  # 只看正常笔记
    if chapter_id is not None:
        query = query.filter(models.Note.chapter_id == chapter_id)
    return query.order_by(models.Note.updated_at.desc()).all()


def create_note(db: Session, user_id: int, note_data: schemas.NoteCreate):
    note = models.Note(user_id=user_id, **note_data.dict())
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def update_note(db: Session, note_id: int, note_data: schemas.NoteCreate):
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if note:
        note.title = note_data.title
        note.content = note_data.content
        note.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(note)
    return note


def delete_note(db: Session, note_id: int, user_id: int):
    """软删除：移入废纸篓"""
    note = db.query(models.Note).filter(models.Note.id == note_id, models.Note.user_id == user_id).first()
    if note:
        note.is_deleted = True
        note.deleted_at = datetime.utcnow()
        db.commit()
        return True
    return False


def restore_note(db: Session, note_id: int, user_id: int):
    """从废纸篓恢复"""
    note = db.query(models.Note).filter(models.Note.id == note_id, models.Note.user_id == user_id, models.Note.is_deleted == True).first()
    if note:
        note.is_deleted = False
        note.deleted_at = None
        db.commit()
        return True
    return False


def permanent_delete_note(db: Session, note_id: int, user_id: int):
    """永久删除"""
    note = db.query(models.Note).filter(models.Note.id == note_id, models.Note.user_id == user_id).first()
    if note:
        db.delete(note)
        db.commit()
        return True
    return False


def empty_trash(db: Session, user_id: int):
    """清空废纸篓"""
    count = db.query(models.Note).filter(models.Note.user_id == user_id, models.Note.is_deleted == True).delete()
    db.commit()
    return count


def get_progress(db: Session, user_id: int):
    return db.query(models.UserProgress).filter(models.UserProgress.user_id == user_id).order_by(models.UserProgress.chapter_id).all()


def update_progress(db: Session, user_id: int, chapter_id: int, status: str):
    progress = db.query(models.UserProgress).filter(models.UserProgress.user_id == user_id, models.UserProgress.chapter_id == chapter_id).first()
    if not progress:
        progress = models.UserProgress(user_id=user_id, chapter_id=chapter_id, status=status)
        db.add(progress)
    else:
        progress.status = status
        progress.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(progress)
    return progress


def get_questions(
    db: Session,
    chapter_id: int,
    question_types: list[str] | None = None,
    difficulty: str | None = None,
    limit: int = 10,
):
    """随机抽取符合条件的题目，不返回答案。"""
    from sqlalchemy.sql.expression import func

    q = db.query(models.Question).filter(models.Question.chapter_id == chapter_id)
    if question_types:
        q = q.filter(models.Question.question_type.in_(question_types))
    if difficulty:
        q = q.filter(models.Question.difficulty == difficulty)
    return q.order_by(func.random()).limit(limit).all()


def get_question_by_id(db: Session, question_id: int):
    return db.query(models.Question).filter(models.Question.id == question_id).first()
