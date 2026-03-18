from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from pydantic import BaseModel
from database import get_db
from models import CambridgeBook, CambridgeTest, CambridgeSection, UserListeningScore

router = APIRouter(prefix="/listening", tags=["Listening"])


# ---------- Request body model ----------

class SubmitScoreRequest(BaseModel):
    section_id: int
    correct_num: int
    total_num: int = 10
    user_id: int


# ---------- Endpoints ----------

@router.get("/cambridge")
def get_cambridge_list(db: Session = Depends(get_db)):
    """Return all available Cambridge IELTS books."""
    books = (
        db.query(CambridgeBook)
        .filter(CambridgeBook.is_available == 1)
        .order_by(CambridgeBook.cambridge_id)
        .all()
    )
    return [{"cambridge_id": b.cambridge_id, "book_name": b.book_name} for b in books]


@router.get("/tests")
def get_tests(cambridge_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Return all available tests for a given Cambridge book,
    including how many sections the user has completed.
    """
    tests = (
        db.query(CambridgeTest)
        .filter(CambridgeTest.cambridge_id == cambridge_id, CambridgeTest.is_available == 1)
        .order_by(CambridgeTest.test_no)
        .all()
    )
    if not tests:
        raise HTTPException(status_code=404, detail=f"No tests found for Cambridge book {cambridge_id}")

    result = []
    for test in tests:
        total_sections = (
            db.query(func.count(CambridgeSection.section_id))
            .filter(CambridgeSection.test_id == test.test_id)
            .scalar()
        )
        completed_sections = (
            db.query(func.count(UserListeningScore.score_id))
            .join(CambridgeSection, UserListeningScore.section_id == CambridgeSection.section_id)
            .filter(
                CambridgeSection.test_id == test.test_id,
                UserListeningScore.user_id == user_id,
            )
            .scalar()
        )
        result.append({
            "test_id": test.test_id,
            "test_no": test.test_no,
            "total_sections": total_sections,
            "completed_sections": completed_sections,
        })
    return result


@router.get("/sections")
def get_sections(test_id: int, db: Session = Depends(get_db)):
    """Return all sections for a given test_id."""
    sections = (
        db.query(CambridgeSection)
        .filter(CambridgeSection.test_id == test_id)
        .order_by(CambridgeSection.section_no)
        .all()
    )
    if not sections:
        raise HTTPException(status_code=404, detail="No sections found for this test")
    return [
        {"section_id": s.section_id, "section_no": s.section_no, "section_name": s.section_name}
        for s in sections
    ]


@router.get("/material")
def get_listening_material(section_id: int, db: Session = Depends(get_db)):
    """Return audio path, image path, and answer key for a given section_id."""
    section = db.query(CambridgeSection).filter(CambridgeSection.section_id == section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    return {
        "audio": section.audio_path,
        "image": section.image_path,
        "answers": section.answers,
    }


@router.post("/submit")
def submit_score(body: SubmitScoreRequest, db: Session = Depends(get_db)):
    """
    Submit or update the user's score for a section.
    Each user can only have one score record per section (upsert behaviour).
    """
    section = db.query(CambridgeSection).filter(CambridgeSection.section_id == body.section_id).first()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")

    existing = (
        db.query(UserListeningScore)
        .filter(
            UserListeningScore.user_id == body.user_id,
            UserListeningScore.section_id == body.section_id,
        )
        .first()
    )
    if existing:
        existing.correct_num = body.correct_num
        existing.total_num = body.total_num
    else:
        db.add(UserListeningScore(
            user_id=body.user_id,
            section_id=body.section_id,
            correct_num=body.correct_num,
            total_num=body.total_num,
        ))
    db.commit()
    return {"status": "success", "message": "Score submitted successfully"}
