from datetime import date, timedelta, datetime as _datetime

import json
import os

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.encoders import ENCODERS_BY_TYPE
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .ai_provider import AIProviderError, generate_answer, generate_answer_stream, generate_resource_content
from .database import engine, get_db

_ENCODE_DT = ENCODERS_BY_TYPE[_datetime]
ENCODERS_BY_TYPE[_datetime] = lambda dt: _ENCODE_DT(dt) + ('Z' if dt.tzinfo is None else '')

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="LearnAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.types import ASGIApp, Scope, Receive, Send


class NoCacheMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        async def send_no_cache(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"cache-control"] = b"no-cache, no-store, must-revalidate"
                headers[b"pragma"] = b"no-cache"
                headers[b"expires"] = b"0"
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_no_cache)


app.add_middleware(NoCacheMiddleware)


@app.post("/api/users/register", response_model=schemas.UserOut)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    existing = crud.get_user_by_username(db, user.username)
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    new_user = crud.create_user(db, user)
    return new_user


@app.post("/api/users/login", response_model=schemas.UserOut)
def login_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, user.username)
    if not db_user or not crud.verify_password(user.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    return db_user


@app.get("/api/profiles/{user_id}", response_model=schemas.ProfileOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(models.Profile).filter(models.Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@app.post("/api/profiles/{user_id}", response_model=schemas.ProfileOut)
def update_profile(user_id: int, profile: schemas.ProfileBase, db: Session = Depends(get_db)):
    db_profile = crud.create_profile(db, user_id, profile)
    return db_profile


@app.post("/api/subjects", response_model=schemas.SubjectOut)
def create_subject(payload: schemas.SubjectCreate, db: Session = Depends(get_db)):
    existing = db.query(models.Subject).filter(models.Subject.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="该学科已存在")
    subject = models.Subject(
        name=payload.name,
        category=payload.category,
        description=payload.description or "",
    )
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@app.get("/api/subjects", response_model=list[schemas.SubjectOut])
def list_subjects(db: Session = Depends(get_db), category: str | None = Query(None)):
    subjects = crud.get_subjects(db)
    if category:
        subjects = [s for s in subjects if s.category == category]
    return subjects


@app.get("/api/subjects/{subject_id}", response_model=schemas.SubjectOut)
def subject_detail(subject_id: int, db: Session = Depends(get_db)):
    subject = crud.get_subject(db, subject_id)
    if not subject:
        raise HTTPException(status_code=404, detail="学科未找到")
    return subject


@app.delete("/api/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_subject(db, subject_id)
    if not ok:
        raise HTTPException(status_code=404, detail="学科未找到")
    return {"detail": "课程已删除"}


@app.get("/api/subjects/{subject_id}/chapters", response_model=list[schemas.ChapterOut])
def chapters_for_subject(subject_id: int, db: Session = Depends(get_db)):
    return crud.get_chapters_by_subject(db, subject_id)


@app.get("/api/chapters/{chapter_id}/resources", response_model=list[schemas.ResourceOut])
def chapter_resources(chapter_id: int, db: Session = Depends(get_db)):
    return crud.get_resource_for_chapter(db, chapter_id)


@app.post("/api/chapters/{chapter_id}/resources/generate", response_model=list[schemas.ResourceOut])
def generate_resource(chapter_id: int, payload: schemas.ResourceGenerateRequest, db: Session = Depends(get_db)):
    chapter = crud.get_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节未找到")

    results = []
    for rtype in payload.resource_types:
        try:
            content = generate_resource_content("deepseek", chapter.title, chapter.summary or "", rtype)
        except Exception:
            content = f"（{rtype}生成失败，请稍后重试）"

        resource = models.Resource(
            subject_id=chapter.subject_id,
            chapter_id=chapter.id,
            title=f"{chapter.title} - {rtype}",
            resource_type=rtype,
            content=content,
            is_public=True,
            view_count=0,
        )
        results.append(crud.create_resource(db, resource))

    return results


@app.post("/api/ai/chat", response_model=schemas.AIChatResponse)
def ai_chat(payload: schemas.AIChatRequest, db: Session = Depends(get_db)):
    chapter = None
    if payload.chapter_id is not None:
        chapter = crud.get_chapter(db, payload.chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="章节未找到")

    if not crud.get_user(db, payload.user_id):
        raise HTTPException(status_code=404, detail="用户未找到")

    role_prompts = {
        "tutor": "你是一个大学数学学习助手「答疑智能体」。请针对用户当前学习的章节内容，耐心解答问题，给出清晰详细的解释。",
        "profile": "你是一个学习画像分析师「画像智能体」。请根据用户的学习情况、已掌握的知识点和薄弱环节，分析用户的能力画像，给出个性化的学习建议。",
        "path": "你是一个学习路径规划师「路径智能体」。请根据用户当前学习进度和目标，规划最优的学习路径，推荐下一步应该学习的内容。",
    }
    role_prompt = role_prompts.get(payload.agent_role, role_prompts["tutor"])

    chapter_context = ""
    if chapter:
        chapter_context = f"当前章节：{chapter.title}。章节简介：{chapter.summary}"

    full_prompt = f"{role_prompt}\n{chapter_context}\n用户问题：{payload.prompt}"

    try:
        answer = generate_answer(payload.provider, full_prompt, {
            "subject_id": payload.subject_id,
            "chapter_id": payload.chapter_id,
            "user_id": payload.user_id,
        })
    except AIProviderError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    crud.save_conversation(db, payload.user_id, payload.subject_id, payload.chapter_id, payload.prompt, answer)
    return {"answer": answer}


@app.post("/api/ai/chat/stream")
def ai_chat_stream(payload: schemas.AIChatRequest, db: Session = Depends(get_db)):
    chapter = None
    if payload.chapter_id is not None:
        chapter = crud.get_chapter(db, payload.chapter_id)
        if not chapter:
            raise HTTPException(status_code=404, detail="章节未找到")

    if not crud.get_user(db, payload.user_id):
        raise HTTPException(status_code=404, detail="用户未找到")

    role_prompts = {
        "tutor": "你是一个大学数学学习助手「答疑智能体」。请针对用户当前学习的章节内容，耐心解答问题，给出清晰详细的解释。",
        "profile": "你是一个学习画像分析师「画像智能体」。请根据用户的学习情况、已掌握的知识点和薄弱环节，分析用户的能力画像，给出个性化的学习建议。",
        "path": "你是一个学习路径规划师「路径智能体」。请根据用户当前学习进度和目标，规划最优的学习路径，推荐下一步应该学习的内容。",
    }
    role_prompt = role_prompts.get(payload.agent_role, role_prompts["tutor"])

    chapter_context = ""
    if chapter:
        chapter_context = f"当前章节：{chapter.title}。章节简介：{chapter.summary}"

    full_prompt = f"{role_prompt}\n{chapter_context}\n用户问题：{payload.prompt}"

    user_context = {
        "subject_id": payload.subject_id,
        "chapter_id": payload.chapter_id,
        "user_id": payload.user_id,
    }

    def sse_generator():
        full_answer = ""
        try:
            for token in generate_answer_stream(payload.provider, full_prompt, user_context):
                full_answer += token
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"
        except Exception:
            yield f"data: {json.dumps({'token': '[生成失败，请稍后重试]'}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        if full_answer:
            crud.save_conversation(db, payload.user_id, payload.subject_id, payload.chapter_id, payload.prompt, full_answer)

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@app.get("/api/ai/history/{user_id}")
def ai_history(user_id: int, chapter_id: int | None = None, db: Session = Depends(get_db)):
    conversations = db.query(models.Conversation).filter(
        models.Conversation.user_id == user_id
    )
    if chapter_id is not None:
        conversations = conversations.filter(models.Conversation.chapter_id == chapter_id)
    conversations = conversations.order_by(models.Conversation.created_at.desc()).limit(30).all()

    return [
        {
            "id": c.id,
            "chapter_id": c.chapter_id,
            "prompt": c.prompt,
            "response": c.response[:200],
            "created_at": c.created_at.isoformat(),
        }
        for c in conversations
    ]


@app.post("/api/quiz/generate")
def generate_quiz(payload: schemas.QuizRequest, db: Session = Depends(get_db)):
    chapter = crud.get_chapter(db, payload.chapter_id) if payload.chapter_id else None
    if payload.chapter_id and not chapter:
        raise HTTPException(status_code=404, detail="章节未找到")

    if payload.question_ids:
        questions = [crud.get_question_by_id(db, qid) for qid in payload.question_ids]
        questions = [q for q in questions if q is not None]
    else:
        questions = crud.get_questions(
            db,
            chapter_id=payload.chapter_id,
            question_types=payload.question_types,
            difficulty=payload.difficulty,
            limit=payload.count,
        )

    result = []
    for q in questions:
        result.append({
            "id": q.id,
            "question_type": q.question_type,
            "difficulty": q.difficulty,
            "content": q.content,
            "options": q.options,
        })

    return {
        "chapter_id": payload.chapter_id,
        "chapter_title": chapter.title if chapter else "",
        "questions": result,
    }


@app.post("/api/quiz/submit")
def submit_quiz(user_id: int, payload: schemas.QuizSubmit, db: Session = Depends(get_db)):
    chapter = crud.get_chapter(db, payload.chapter_id) if payload.chapter_id else None
    if payload.chapter_id and not chapter:
        raise HTTPException(status_code=404, detail="章节未找到")

    if len(payload.question_ids) != len(payload.answers):
        raise HTTPException(status_code=400, detail="答案数量与题目数量不匹配")

    total = len(payload.question_ids)
    wrong_items = []
    all_items = []
    score = 0

    for qid, user_answer in zip(payload.question_ids, payload.answers):
        question = crud.get_question_by_id(db, qid)
        if not question:
            continue
        correct = question.answer.strip()
        user = user_answer.strip()
        is_correct = (user.lower() == correct.lower() or user == correct)
        if is_correct:
            score += 1
        else:
            wrong_items.append({
                "question_id": qid,
                "content": question.content[:80],
                "your_answer": user_answer,
                "correct_answer": correct,
            })
        all_items.append({
            "question_id": qid,
            "content": question.content,
            "question_type": question.question_type,
            "your_answer": user_answer,
            "correct_answer": correct,
            "explanation": question.explanation or "",
            "is_correct": is_correct,
        })

    record = crud.save_quiz_record(
        db, user_id, payload.chapter_id,
        score, total,
        json.dumps(wrong_items, ensure_ascii=False),
    )
    return {
        "record": {
            "id": record.id,
            "user_id": record.user_id,
            "chapter_id": record.chapter_id,
            "score": record.score,
            "total_questions": record.total_questions,
            "wrong_items": record.wrong_items,
            "created_at": record.created_at.isoformat(),
        },
        "details": all_items,
    }


@app.get("/api/quiz/history/{user_id}")
def quiz_history(user_id: int, db: Session = Depends(get_db)):
    records = crud.get_quiz_history(db, user_id)
    return [schemas.QuizRecordOut.model_validate(r).model_dump(mode='json') for r in records]


@app.get("/api/notes/{user_id}", response_model=list[schemas.NoteOut])
def list_notes(user_id: int, chapter_id: int | None = None, trash: bool = False, db: Session = Depends(get_db)):
    return crud.get_notes(db, user_id, chapter_id, include_deleted=trash)


@app.post("/api/notes/{user_id}/restore/{note_id}")
def restore_note(user_id: int, note_id: int, db: Session = Depends(get_db)):
    ok = crud.restore_note(db, note_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="笔记未找到")
    return {"detail": "已恢复"}


@app.delete("/api/notes/{user_id}/permanent/{note_id}")
def permanent_delete_note(user_id: int, note_id: int, db: Session = Depends(get_db)):
    ok = crud.permanent_delete_note(db, note_id, user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="笔记未找到")
    return {"detail": "已永久删除"}


@app.post("/api/notes/{user_id}/empty-trash")
def empty_trash(user_id: int, db: Session = Depends(get_db)):
    count = crud.empty_trash(db, user_id)
    return {"detail": f"已清空 {count} 条笔记"}


@app.post("/api/notes/{user_id}", response_model=schemas.NoteOut)
def create_note(user_id: int, note: schemas.NoteCreate, db: Session = Depends(get_db)):
    return crud.create_note(db, user_id, note)


@app.put("/api/notes/{user_id}/{note_id}", response_model=schemas.NoteOut)
def update_note(user_id: int, note_id: int, note: schemas.NoteCreate, db: Session = Depends(get_db)):
    updated = crud.update_note(db, note_id, note)
    if not updated:
        raise HTTPException(status_code=404, detail="笔记未找到")
    return updated


@app.delete("/api/notes/{user_id}/{note_id}")
def delete_note(user_id: int, note_id: int, db: Session = Depends(get_db)):
    deleted = crud.delete_note(db, note_id, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="笔记未找到")
    return {"detail": "删除成功"}


@app.get("/api/progress/{user_id}", response_model=list[schemas.ProgressOut])
def list_progress(user_id: int, db: Session = Depends(get_db)):
    return crud.get_progress(db, user_id)


@app.post("/api/progress/{user_id}", response_model=schemas.ProgressOut)
def set_progress(user_id: int, payload: schemas.ProgressUpdate, db: Session = Depends(get_db)):
    return crud.update_progress(db, user_id, payload.chapter_id, payload.status)


@app.get("/api/chapters/{chapter_id}/subsections", response_model=list[schemas.SubsectionOut])
def list_subsections(chapter_id: int, db: Session = Depends(get_db)):
    return crud.get_subsections_by_chapter(db, chapter_id)


@app.post("/api/chapters/{chapter_id}/subsections", response_model=schemas.SubsectionOut)
def create_subsection(chapter_id: int, payload: schemas.SubsectionCreate, db: Session = Depends(get_db)):
    chapter = crud.get_chapter(db, chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="章节未找到")
    return crud.create_subsection(db, chapter_id, payload)


@app.put("/api/subsections/{subsection_id}", response_model=schemas.SubsectionOut)
def update_subsection(subsection_id: int, payload: schemas.SubsectionCreate, db: Session = Depends(get_db)):
    updated = crud.update_subsection(db, subsection_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="小节未找到")
    return updated


@app.delete("/api/subsections/{subsection_id}")
def delete_subsection(subsection_id: int, db: Session = Depends(get_db)):
    ok = crud.delete_subsection(db, subsection_id)
    if not ok:
        raise HTTPException(status_code=404, detail="小节未找到")
    return {"detail": "删除成功"}


@app.post("/api/subsections/{subsection_id}/progress", response_model=schemas.SubsectionProgressOut)
def mark_subsection_progress(subsection_id: int, payload: schemas.SubsectionProgressCreate, db: Session = Depends(get_db)):
    prog = crud.set_subsection_progress(db, payload.user_id, subsection_id, payload.status)
    return prog


@app.get("/api/subsections/{subsection_id}/progress/{user_id}", response_model=schemas.SubsectionProgressOut | None)
def get_subsection_progress(subsection_id: int, user_id: int, db: Session = Depends(get_db)):
    prog = crud.get_subsection_progress(db, user_id, subsection_id)
    return prog


@app.post("/api/checkin/{user_id}")
def checkin(user_id: int, db: Session = Depends(get_db)):
    today = date.today().isoformat()
    existing = db.query(models.Checkin).filter(
        models.Checkin.user_id == user_id,
        models.Checkin.checkin_date == today,
    ).first()
    if existing:
        return {"detail": "今天已打卡", "streak": get_streak(db, user_id)}

    db.add(models.Checkin(user_id=user_id, checkin_date=today))
    db.commit()
    streak = get_streak(db, user_id)
    return {"detail": "打卡成功", "streak": streak, "date": today}


@app.post("/api/resources/{resource_id}/fav")
def resource_fav(resource_id: int, db: Session = Depends(get_db)):
    r = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if r:
        r.fav_count = (r.fav_count or 0) + 1
        db.commit()
        return {"fav_count": r.fav_count}
    raise HTTPException(status_code=404)


def get_streak(db: Session, user_id: int) -> int:
    today = date.today()
    streak = 0
    for i in range(365):
        d = today - timedelta(days=i)
        record = db.query(models.Checkin).filter(
            models.Checkin.user_id == user_id,
            models.Checkin.checkin_date == d.isoformat(),
        ).first()
        if record:
            streak += 1
        else:
            break
    return streak


@app.get("/api/dashboard/{user_id}")
def get_dashboard(user_id: int, db: Session = Depends(get_db)):
    from datetime import date as _date, timedelta as _td

    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")

    profile = db.query(models.Profile).filter(models.Profile.user_id == user_id).first()
    display_name = (profile.name if profile and profile.name else user.username)

    today = _date.today()
    today_str = today.isoformat()
    streak = get_streak(db, user_id)
    checked_today = db.query(models.Checkin).filter(
        models.Checkin.user_id == user_id,
        models.Checkin.checkin_date == today_str,
    ).first() is not None

    last_progress = db.query(models.UserProgress).filter(
        models.UserProgress.user_id == user_id,
        models.UserProgress.status == "学习中",
    ).order_by(models.UserProgress.updated_at.desc()).first()

    continue_learning = None
    if last_progress:
        ch = db.query(models.Chapter).filter(models.Chapter.id == last_progress.chapter_id).first()
        if ch:
            subj = db.query(models.Subject).filter(models.Subject.id == ch.subject_id).first()
            total_chs = db.query(models.Chapter).filter(models.Chapter.subject_id == ch.subject_id).count()
            completed_chs = db.query(models.UserProgress).filter(
                models.UserProgress.user_id == user_id,
                models.UserProgress.status.in_(["已完成", "学习中"]),
                models.UserProgress.chapter_id.in_(
                    [c.id for c in db.query(models.Chapter).filter(models.Chapter.subject_id == ch.subject_id).all()]
                )
            ).count()
            continue_learning = {
                "chapter_id": ch.id, "chapter_title": ch.title,
                "subject_id": ch.subject_id, "subject_name": subj.name if subj else "",
                "total_chapters": total_chs, "completed_chapters": completed_chs,
            }

    if not continue_learning:
        try:
            first_subject = db.query(models.Subject).order_by(models.Subject.id).first()
            if first_subject:
                first_ch = db.query(models.Chapter).filter(models.Chapter.subject_id == first_subject.id).order_by(models.Chapter.order).first()
                total = db.query(models.Chapter).filter(models.Chapter.subject_id == first_subject.id).count()
                continue_learning = {
                    "chapter_id": first_ch.id if first_ch else 1,
                    "chapter_title": first_ch.title if first_ch else "",
                    "subject_id": first_subject.id, "subject_name": first_subject.name,
                    "total_chapters": total, "completed_chapters": 0,
                    "is_new": True,
                }
        except Exception:
            continue_learning = {"chapter_id":1,"chapter_title":"","subject_id":1,"subject_name":"","total_chapters":0,"completed_chapters":0,"is_new":True}

    week_start = today - _td(days=today.weekday())
    last_week_start = week_start - _td(days=7)
    this_week_records = db.query(models.QuizRecord).filter(
        models.QuizRecord.user_id == user_id,
        models.QuizRecord.created_at >= week_start.isoformat(),
    ).all()
    last_week_records = db.query(models.QuizRecord).filter(
        models.QuizRecord.user_id == user_id,
        models.QuizRecord.created_at >= last_week_start.isoformat(),
        models.QuizRecord.created_at < week_start.isoformat(),
    ).all()

    weekly_quiz_count = len(this_week_records)
    weekly_avg = round(sum(r.score / r.total_questions * 100 for r in this_week_records) / max(len(this_week_records), 1), 1)
    last_weekly_avg = round(sum(r.score / r.total_questions * 100 for r in last_week_records) / max(len(last_week_records), 1), 1) if last_week_records else 0
    weekly_diff = round(weekly_avg - last_weekly_avg, 1) if last_week_records else 0

    week_days = 0
    for i in range(7):
        d = (week_start + _td(days=i)).isoformat()
        if db.query(models.Checkin).filter(models.Checkin.user_id == user_id, models.Checkin.checkin_date == d).first():
            week_days += 1

    subjects = crud.get_subjects(db)
    courses = []
    for s in subjects:
        chapters = crud.get_chapters_by_subject(db, s.id)
        completed = db.query(models.UserProgress).filter(
            models.UserProgress.user_id == user_id, models.UserProgress.status.in_(["已完成", "学习中"]),
            models.UserProgress.chapter_id.in_([c.id for c in chapters])
        ).count()
        courses.append({
            "id": s.id, "name": s.name, "category": s.category,
            "total_chapters": len(chapters), "completed_chapters": completed,
        })

    recent = build_recent_records(db, user_id, limit=5)

    return {
        "display_name": display_name,
        "streak": streak,
        "checked_today": checked_today,
        "continue_learning": continue_learning,
        "weekly": {
            "quiz_count": weekly_quiz_count if this_week_records else None,
            "avg_accuracy": weekly_avg if this_week_records else None,
            "accuracy_diff": weekly_diff,
            "study_days": week_days,
        },
        "courses": courses,
        "recent_records": recent,
    }


def build_recent_records(db, user_id, limit=5):
    records = []

    progress_list = db.query(models.UserProgress).filter(
        models.UserProgress.user_id == user_id,
    ).order_by(models.UserProgress.updated_at.desc()).limit(limit).all()
    for p in progress_list:
        ch = db.query(models.Chapter).filter(models.Chapter.id == p.chapter_id).first()
        subj = db.query(models.Subject).filter(models.Subject.id == ch.subject_id).first() if ch else None
        records.append({
            "type": "progress",
            "chapter_title": ch.title if ch else f"章节#{p.chapter_id}",
            "subject_name": subj.name if subj else "",
            "subject_id": ch.subject_id if ch else 1,
            "chapter_id": p.chapter_id,
            "detail": "已完成" if p.status == "已完成" else "学习中",
            "time": p.updated_at.isoformat() if p.updated_at else "",
        })

    quiz_list = db.query(models.QuizRecord).filter(
        models.QuizRecord.user_id == user_id,
    ).order_by(models.QuizRecord.created_at.desc()).limit(limit).all()
    for q in quiz_list:
        ch = db.query(models.Chapter).filter(models.Chapter.id == q.chapter_id).first()
        subj = db.query(models.Subject).filter(models.Subject.id == ch.subject_id).first() if ch else None
        pct = round(q.score / q.total_questions * 100)
        records.append({
            "type": "quiz",
            "chapter_title": ch.title if ch else f"章节#{q.chapter_id}",
            "subject_name": subj.name if subj else "",
            "subject_id": ch.subject_id if ch else 1,
            "chapter_id": q.chapter_id,
            "detail": f"{pct}%",
            "score": q.score, "total": q.total_questions,
            "time": q.created_at.isoformat() if q.created_at else "",
        })

    records.sort(key=lambda r: r["time"], reverse=True)
    return records[:limit]


@app.get("/api/checkin/{user_id}")
def get_checkin(user_id: int, db: Session = Depends(get_db)):
    records = db.query(models.Checkin).filter(
        models.Checkin.user_id == user_id
    ).order_by(models.Checkin.checkin_date.desc()).limit(60).all()

    streak = get_streak(db, user_id)
    dates = [r.checkin_date for r in records]

    return {
        "streak": streak,
        "total_days": len(records),
        "dates": dates,
    }


@app.post("/api/resources/{resource_id}/view")
def increment_resource_view(resource_id: int, db: Session = Depends(get_db)):
    resource = db.query(models.Resource).filter(models.Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(status_code=404, detail="Resource not found")
    resource.view_count = (resource.view_count or 0) + 1
    db.commit()
    db.refresh(resource)
    return {"view_count": resource.view_count}


@app.get("/api/resources/public")
def list_public_resources(subject_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(models.Resource).filter(models.Resource.is_public == True)
    if subject_id is not None:
        query = query.filter(models.Resource.subject_id == subject_id)
    resources = query.order_by(models.Resource.created_at.desc()).limit(50).all()

    result = []
    for r in resources:
        subject = db.query(models.Subject).filter(models.Subject.id == r.subject_id).first()
        chapter = db.query(models.Chapter).filter(models.Chapter.id == r.chapter_id).first()
        result.append({
            "id": r.id,
            "subject_id": r.subject_id,
            "chapter_id": r.chapter_id,
            "title": r.title,
            "resource_type": r.resource_type,
            "content": r.content[:300] + ("..." if len(r.content or "") > 300 else ""),
            "content_full": r.content,
            "subject_name": subject.name if subject else "",
            "chapter_title": chapter.title if chapter else "",
            "view_count": r.view_count or 0,
            "created_at": r.created_at.isoformat(),
        })

    return result


@app.post("/api/notes/{user_id}/share/{note_id}")
def share_note(user_id: int, note_id: int, db: Session = Depends(get_db)):
    note = db.query(models.Note).filter(
        models.Note.id == note_id,
        models.Note.user_id == user_id,
        models.Note.is_deleted == False,
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记未找到")
    if not note.content or not note.content.strip():
        raise HTTPException(status_code=400, detail="笔记内容为空，无法分享")

    chapter = db.query(models.Chapter).filter(models.Chapter.id == note.chapter_id).first()
    user = db.query(models.User).filter(models.User.id == user_id).first()
    sharer_name = user.username if user else "匿名"

    resource = models.Resource(
        subject_id=chapter.subject_id if chapter else 1,
        chapter_id=note.chapter_id,
        title=f"📝 {note.title or '无标题'}（by {sharer_name}）",
        resource_type="学霸笔记",
        content=note.content,
        is_public=True,
        view_count=0,
        fav_count=0,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {"detail": "分享成功", "resource_id": resource.id}


@app.get("/api/leaderboard/{subject_id}")
def get_leaderboard(subject_id: int, db: Session = Depends(get_db)):
    from sqlalchemy import func as _func

    chapters = db.query(models.Chapter).filter(models.Chapter.subject_id == subject_id).all()
    chapter_ids = [c.id for c in chapters]

    if not chapter_ids:
        return []

    results = db.query(
        models.QuizRecord.user_id,
        _func.sum(models.QuizRecord.score).label("total_score"),
        _func.count(models.QuizRecord.id).label("attempts"),
        _func.avg(100.0 * models.QuizRecord.score / models.QuizRecord.total_questions).label("avg_pct"),
    ).filter(
        models.QuizRecord.chapter_id.in_(chapter_ids)
    ).group_by(models.QuizRecord.user_id).order_by(_func.sum(models.QuizRecord.score).desc()).limit(20).all()

    leaderboard = []
    for r in results:
        user = db.query(models.User).filter(models.User.id == r.user_id).first()
        profile = db.query(models.Profile).filter(models.Profile.user_id == r.user_id).first()
        leaderboard.append({
            "user_id": r.user_id,
            "username": user.username if user else "未知",
            "display_name": (profile.name if profile and profile.name else user.username) if user else "未知",
            "total_score": r.total_score,
            "attempts": r.attempts,
            "avg_pct": round(r.avg_pct, 1) if r.avg_pct else 0,
        })

    return leaderboard


@app.get("/api/ppts")
def list_public_ppts():
    """公开列出 static/ppts/ 下所有 PPT 文件（测试阶段作为公共资源，无需登录）。"""
    ppt_dir = os.path.join(os.path.dirname(__file__), "..", "static", "ppts")
    items = []
    if os.path.isdir(ppt_dir):
        for fn in sorted(os.listdir(ppt_dir)):
            if fn.lower().endswith(".pptx"):
                fp = os.path.join(ppt_dir, fn)
                items.append({
                    "name": fn,
                    "url": "/ppts/" + fn,
                    "size": os.path.getsize(fp),
                })
    return items


app.mount("/", StaticFiles(directory="static", html=True), name="static")