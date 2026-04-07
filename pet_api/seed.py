from __future__ import annotations

from decimal import Decimal
from sqlalchemy.orm import Session
from . import models

LEVEL_ROWS = [
    {"level": 1, "exp_required": 1500, "unlock_skin_id": None},
    {"level": 2, "exp_required": 2000, "unlock_skin_id": None},
    {"level": 3, "exp_required": 2500, "unlock_skin_id": None},
    {"level": 4, "exp_required": 3000, "unlock_skin_id": None},
    {"level": 5, "exp_required": 3500, "unlock_skin_id": None},
    {"level": 6, "exp_required": 4000, "unlock_skin_id": None},
    {"level": 7, "exp_required": 4500, "unlock_skin_id": None},
    {"level": 8, "exp_required": 5000, "unlock_skin_id": None},
    {"level": 9, "exp_required": 5500, "unlock_skin_id": None},
    {"level": 10, "exp_required": 6000, "unlock_skin_id": None},
    {"level": 11, "exp_required": 6500, "unlock_skin_id": None},
    {"level": 12, "exp_required": 7000, "unlock_skin_id": None},
    {"level": 13, "exp_required": 7500, "unlock_skin_id": None},
    {"level": 14, "exp_required": 8000, "unlock_skin_id": None},
    {"level": 15, "exp_required": 8500, "unlock_skin_id": None},
    {"level": 16, "exp_required": 9000, "unlock_skin_id": None},
    {"level": 17, "exp_required": 9500, "unlock_skin_id": None},
    {"level": 18, "exp_required": 10000, "unlock_skin_id": None},
    {"level": 19, "exp_required": 10500, "unlock_skin_id": None},
]

SKIN_ROWS = [
    {"skin_id": 1, "pet_type_id": 1, "name": "Fox Lv1", "description": "Default fox skin", "gif_url": "/static/pet_gifs/1Level.gif", "unlock_level": 1},
    {"skin_id": 2, "pet_type_id": 1, "name": "Fox Lv3", "description": "Unlocked at level 3", "gif_url": "/static/pet_gifs/3Level.gif", "unlock_level": 3},
    {"skin_id": 3, "pet_type_id": 1, "name": "Fox Lv5", "description": "Unlocked at level 5", "gif_url": "/static/pet_gifs/5Level.gif", "unlock_level": 5},
    {"skin_id": 4, "pet_type_id": 1, "name": "Fox Lv8", "description": "Unlocked at level 8", "gif_url": "/static/pet_gifs/8Level.gif", "unlock_level": 8},
    {"skin_id": 5, "pet_type_id": 1, "name": "Fox Lv10", "description": "Unlocked at level 10", "gif_url": "/static/pet_gifs/10Level.gif", "unlock_level": 10},
    {"skin_id": 6, "pet_type_id": 1, "name": "Fox Lv20", "description": "Unlocked at level 20", "gif_url": "/static/pet_gifs/20Level.gif", "unlock_level": 20},
]

QUOTE_ROWS = [
    {"quote_id": 1, "pet_type_id": 1, "min_vitality": 0, "max_vitality": 20, "content": "I am very hungry..."},
    {"quote_id": 2, "pet_type_id": 1, "min_vitality": 0, "max_vitality": 20, "content": "Please study with me soon..."},
    {"quote_id": 3, "pet_type_id": 1, "min_vitality": 21, "max_vitality": 40, "content": "I feel sleepy today."},
    {"quote_id": 4, "pet_type_id": 1, "min_vitality": 41, "max_vitality": 60, "content": "Did you finish your vocabulary today?"},
    {"quote_id": 5, "pet_type_id": 1, "min_vitality": 61, "max_vitality": 80, "content": "Let us keep learning together!"},
    {"quote_id": 6, "pet_type_id": 1, "min_vitality": 81, "max_vitality": 100, "content": "Amazing! We are doing great today!"},
]

SERVICE_CATEGORY_ROWS = [
    {"category_id": 1, "name": "Food"},
    {"category_id": 2, "name": "Clean"},
    {"category_id": 3, "name": "Play"},
]

SERVICE_ROWS = [
    {"service_id": 1, "category_id": 1, "name": "Water", "vitality_effect": Decimal("3.00"), "points_cost": 1, "gif_url": None, "cooldown_seconds": 60},
    {"service_id": 2, "category_id": 1, "name": "Snack", "vitality_effect": Decimal("6.00"), "points_cost": 2, "gif_url": None, "cooldown_seconds": 120},
    {"service_id": 3, "category_id": 1, "name": "Roast Chicken", "vitality_effect": Decimal("10.00"), "points_cost": 5, "gif_url": None, "cooldown_seconds": 300},
    {"service_id": 4, "category_id": 2, "name": "Bath", "vitality_effect": Decimal("12.00"), "points_cost": 6, "gif_url": None, "cooldown_seconds": 600},
    {"service_id": 5, "category_id": 3, "name": "Play Time", "vitality_effect": Decimal("8.00"), "points_cost": 4, "gif_url": None, "cooldown_seconds": 300},
]


def _upsert_by_pk(db: Session, model_cls, pk_name: str, row: dict) -> None:
    obj = db.get(model_cls, row[pk_name])
    if obj is None:
        db.add(model_cls(**row))
        return
    for key, value in row.items():
        setattr(obj, key, value)
    db.add(obj)


def seed_data(db: Session) -> None:
    pet_type = db.get(models.PetType, 1)
    if pet_type is None:
        pet_type = models.PetType(pet_type_id=1, name="Fox", description="A fox that grows with your study progress.", default_skin_id=None)
        db.add(pet_type)
    else:
        pet_type.name = "Fox"
        pet_type.description = "A fox that grows with your study progress."
        pet_type.default_skin_id = None
        db.add(pet_type)
    db.flush()

    for row in SKIN_ROWS:
        _upsert_by_pk(db, models.Skin, "skin_id", row)
    db.flush()

    pet_type.default_skin_id = 1
    db.add(pet_type)

    for row in LEVEL_ROWS:
        _upsert_by_pk(db, models.LevelConfig, "level", row)
    for row in QUOTE_ROWS:
        _upsert_by_pk(db, models.PetQuote, "quote_id", row)
    for row in SERVICE_CATEGORY_ROWS:
        _upsert_by_pk(db, models.ServiceCategory, "category_id", row)
    db.flush()
    for row in SERVICE_ROWS:
        _upsert_by_pk(db, models.Service, "service_id", row)
    db.flush()
