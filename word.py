from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import WordCategory, WordSubcategory, Word

router = APIRouter(prefix="/word", tags=["Word"])


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """Return all top-level word categories."""
    results = db.query(WordCategory).all()
    return [{"category_id": c.category_id, "category_name": c.category_name} for c in results]


@router.get("/subcategories")
def get_subcategories(category_id: int, db: Session = Depends(get_db)):
    """Return all sub-categories under a given category_id."""
    results = (
        db.query(WordSubcategory)
        .filter(WordSubcategory.category_id == category_id)
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail=f"Category {category_id} not found or has no subcategories")
    return [{"subcategory_id": s.subcategory_id, "subcategory_name": s.subcategory_name} for s in results]


@router.get("/words")
def get_words(subcategory_id: int, db: Session = Depends(get_db)):
    """Return all words under a given subcategory_id."""
    words = (
        db.query(Word)
        .filter(Word.subcategory_id == subcategory_id)
        .all()
    )
    if not words:
        raise HTTPException(status_code=404, detail="No words found for this subcategory")
    return [{"english": w.english, "chinese": w.explanation} for w in words]

