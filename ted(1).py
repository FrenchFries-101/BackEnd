from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from database import get_db
from sqlalchemy import Column, Integer, BigInteger, String, Text, DateTime, JSON, ForeignKey, SmallInteger, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

router = APIRouter(prefix="/ted", tags=["TED"])

class UserListeningScore(Base):
    __tablename__ = "t_user_listening_score"

    score_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    section_id = Column(BigInteger, ForeignKey("t_cambridge_section.section_id"), nullable=False)
    correct_num = Column(Integer, nullable=False)
    total_num = Column(Integer, nullable=False, default=10)
    submit_time = Column(DateTime, default=datetime.utcnow)

    section = relationship("CambridgeSection", back_populates="scores")


class TedTalk(Base):
    __tablename__ = "t_ted_talk"

    talk_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    youtube_url = Column(String(255), nullable=False)
    audio_path = Column(String(255), default=None)
    subtitle = Column(Text, nullable=False)
    is_available = Column(SmallInteger, nullable=False, default=1)
    create_time = Column(DateTime, default=datetime.utcnow)

    questions = relationship("TedQuestion", back_populates="talk")


class TedQuestion(Base):
    __tablename__ = "t_ted_question"

    question_id = Column(BigInteger, primary_key=True, autoincrement=True)
    talk_id = Column(Integer, ForeignKey("t_ted_talk.talk_id"), nullable=False)
    question_type = Column(
        Enum("sentence_completion", "true_false_not_given", "multiple_choice"),
        nullable=False
    )
    question_text = Column(String(500), nullable=False)
    options = Column(JSON, default=None)
    answer = Column(String(100), nullable=False)
    explanation = Column(String(500), default=None)
    create_time = Column(DateTime, default=datetime.utcnow)

    talk = relationship("TedTalk", back_populates="questions")


class UserTedScore(Base):
    __tablename__ = "t_user_ted_score"

    score_id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    talk_id = Column(Integer, ForeignKey("t_ted_talk.talk_id"), nullable=False)
    correct_num = Column(Integer, nullable=False)
    total_num = Column(Integer, nullable=False)
    submit_time = Column(DateTime, default=datetime.utcnow)

@router.get("/talks")
def get_talks(db: Session = Depends(get_db)):
    """Return all available TED talks (title, audio URL, youtube URL)."""
    talks = (
        db.query(TedTalk)
        .filter(TedTalk.is_available == 1)
        .order_by(TedTalk.talk_id)
        .all()
    )
    return [
        {
            "talk_id": t.talk_id,
            "title": t.title,
            "youtube_url": t.youtube_url,
            "audio_path": t.audio_path,
        }
        for t in talks
    ]


@router.get("/questions")
def load_question(talk_id: int, db: Session = Depends(get_db)):
    """Return all questions for a given TED talk, grouped by type."""
    talk = db.query(TedTalk).filter(TedTalk.talk_id == talk_id).first()
    if not talk:
        raise HTTPException(status_code=404, detail="TED talk not found")

    questions = (
        db.query(TedQuestion)
        .filter(TedQuestion.talk_id == talk_id)
        .order_by(TedQuestion.question_type, TedQuestion.question_id)
        .all()
    )

    result = {"talk_id": talk_id, "title": talk.title, "questions": []}
    for q in questions:
        result["questions"].append({
            "question_id": q.question_id,
            "question_type": q.question_type,
            "question_text": q.question_text,
            "options": q.options,
        })
    return result


class SubmitAnswerRequest(BaseModel):
    user_id: int
    talk_id: int
    answer_list: List[str]  # answers in the same order as /ted/questions returns


@router.post("/submit")
def submit_answer(body: SubmitAnswerRequest, db: Session = Depends(get_db)):
    """
    Submit answers for a TED talk. Returns score and per-question feedback.
    answer_list must match the order of questions returned by GET /ted/questions.
    """
    talk = db.query(TedTalk).filter(TedTalk.talk_id == body.talk_id).first()
    if not talk:
        raise HTTPException(status_code=404, detail="TED talk not found")

    questions = (
        db.query(TedQuestion)
        .filter(TedQuestion.talk_id == body.talk_id)
        .order_by(TedQuestion.question_type, TedQuestion.question_id)
        .all()
    )

    if len(body.answer_list) != len(questions):
        raise HTTPException(
            status_code=400,
            detail=f"Expected {len(questions)} answers, got {len(body.answer_list)}"
        )

    correct_num = 0
    feedback = []
    for q, submitted in zip(questions, body.answer_list):
        is_correct = q.answer.strip().lower() == submitted.strip().lower()
        if is_correct:
            correct_num += 1
        feedback.append({
            "question_id": q.question_id,
            "is_correct": is_correct,
        })

    total_num = len(questions)

    # Upsert: overwrite if user already submitted for this talk
    existing = (
        db.query(UserTedScore)
        .filter(UserTedScore.user_id == body.user_id, UserTedScore.talk_id == body.talk_id)
        .first()
    )
    if existing:
        existing.correct_num = correct_num
        existing.total_num = total_num
    else:
        db.add(UserTedScore(
            user_id=body.user_id,
            talk_id=body.talk_id,
            correct_num=correct_num,
            total_num=total_num,
        ))
    db.commit()

    return {
        "status": "success",
        "correct_num": correct_num,
        "total_num": total_num,
        "feedback": feedback,
    }

@router.get("/analysis")
def load_analysis(talk_id: int, question_id: int, db: Session = Depends(get_db)):
    question = db.query(TedQuestion).filter(TedQuestion.talk_id == talk_id, TedQuestion.question_id == question_id).first()
    if question:
        result = {"Question_id": question_id, "Analysis": question.explanation}
        return result
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Fail to find TED {talk_id} question {question_id}."
        )

