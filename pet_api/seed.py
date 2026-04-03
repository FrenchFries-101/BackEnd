from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


LEVEL_ROWS = [
    {"level": 1, "exp_required": 1500, "unlock_skin_id": None},
    {"level": 2, "exp_required": 2000, "unlock_skin_id": 2},
    {"level": 3, "exp_required": 2500, "unlock_skin_id": None},
    {"level": 4, "exp_required": 3000, "unlock_skin_id": 3},
    {"level": 5, "exp_required": 3500, "unlock_skin_id": None},
    {"level": 6, "exp_required": 4000, "unlock_skin_id": 4},
    {"level": 7, "exp_required": 4000, "unlock_skin_id": None},
    {"level": 8, "exp_required": 5500, "unlock_skin_id": 5},
    {"level": 9, "exp_required": 6000, "unlock_skin_id": 6},
]

SKIN_ROWS = [
    {"skin_id": 1, "pet_type_id": 1, "name": "Default Dog", "description": "Starter skin", "gif_url": "dog1.gif", "unlock_level": 1},
    {"skin_id": 2, "pet_type_id": 1, "name": "Sunny Dog", "description": "Unlocked at level 2", "gif_url": "dog2.gif", "unlock_level": 2},
    {"skin_id": 3, "pet_type_id": 1, "name": "Sport Dog", "description": "Unlocked at level 4", "gif_url": "dog3.gif", "unlock_level": 4},
    {"skin_id": 4, "pet_type_id": 1, "name": "Gentleman Dog", "description": "Unlocked at level 6", "gif_url": "dog4.gif", "unlock_level": 6},
    {"skin_id": 5, "pet_type_id": 1, "name": "Ninja Dog", "description": "Unlocked at level 8", "gif_url": "dog5.gif", "unlock_level": 8},
    {"skin_id": 6, "pet_type_id": 1, "name": "Legend Dog", "description": "Unlocked at level 10", "gif_url": "dog6.gif", "unlock_level": 10},
]

QUOTE_ROWS = [
    {"pet_type_id": 1, "min_vitality": 0, "max_vitality": 20, "content": "I am really hungry..."},
    {"pet_type_id": 1, "min_vitality": 0, "max_vitality": 20, "content": "Please do not forget me..."},
    {"pet_type_id": 1, "min_vitality": 21, "max_vitality": 40, "content": "I feel so tired today."},
    {"pet_type_id": 1, "min_vitality": 41, "max_vitality": 60, "content": "Did you study your words today?"},
    {"pet_type_id": 1, "min_vitality": 61, "max_vitality": 80, "content": "Let us keep learning together!"},
    {"pet_type_id": 1, "min_vitality": 81, "max_vitality": 100, "content": "Today feels amazing!"},
]

SERVICE_CATEGORY_ROWS = [
    {"category_id": 1, "name": "Food"},
    {"category_id": 2, "name": "Clean"},
    {"category_id": 3, "name": "Play"},
]

SERVICE_ROWS = [
    {"service_id": 1, "category_id": 1, "name": "Water", "vitality_effect": Decimal("3.00"), "points_cost": 1, "gif_url": "water.gif", "cooldown_seconds": 60},
    {"service_id": 2, "category_id": 1, "name": "Carrot", "vitality_effect": Decimal("6.00"), "points_cost": 2, "gif_url": "carrot.gif", "cooldown_seconds": 120},
    {"service_id": 3, "category_id": 1, "name": "Cake", "vitality_effect": Decimal("8.00"), "points_cost": 4, "gif_url": "cake.gif", "cooldown_seconds": 240},
    {"service_id": 4, "category_id": 1, "name": "Roast Chicken", "vitality_effect": Decimal("10.00"), "points_cost": 5, "gif_url": "chicken.gif", "cooldown_seconds": 300},
    {"service_id": 5, "category_id": 2, "name": "Bath", "vitality_effect": Decimal("12.00"), "points_cost": 6, "gif_url": "bath.gif", "cooldown_seconds": 600},
    {"service_id": 6, "category_id": 3, "name": "Play Time", "vitality_effect": Decimal("8.00"), "points_cost": 4, "gif_url": "play.gif", "cooldown_seconds": 300},
]


def seed_data(db: Session) -> None:
    has_pet_type = db.scalar(select(models.PetType.pet_type_id).limit(1))
    if has_pet_type is not None:
        return

    for row in SKIN_ROWS:
        db.add(models.Skin(**row))
    db.flush()

    db.add(models.PetType(pet_type_id=1, name="Dog", description="A loyal study companion.", default_skin_id=1))

    for row in LEVEL_ROWS:
        db.add(models.LevelConfig(**row))

    for row in QUOTE_ROWS:
        db.add(models.PetQuote(**row))

    for row in SERVICE_CATEGORY_ROWS:
        db.add(models.ServiceCategory(**row))

    for row in SERVICE_ROWS:
        db.add(models.Service(**row))

    db.flush()
