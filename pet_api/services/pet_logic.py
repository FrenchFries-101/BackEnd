from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional, Set, Union

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pet_api import models

DEC2 = Decimal("0.01")
MAX_LEVEL = 20
VITALITY_DECAY_PER_MIN = Decimal("0.05")
DAILY_POINTS_CAP = 50
TASK_CONFIG = {
    "vocabulary": {"points": 5, "daily_limit": 1, "message": "Vocabulary task completed."},
    "speaking": {"points": 8, "daily_limit": 1, "message": "Speaking task completed."},
    "speaking_excellence": {"points": 5, "daily_limit": 1, "message": "Speaking excellence reward granted."},
    "listening_ielts": {"points": 10, "daily_limit": 1, "message": "IELTS listening task completed."},
    "listening_ted": {"points": 8, "daily_limit": 1, "message": "TED listening task completed."},
    "listening_excellence": {"points": 5, "daily_limit": 1, "message": "Listening excellence reward granted."},
    "forum_post": {"points": 6, "daily_limit": 2, "message": "Forum post reward granted."},
    "forum_liked": {"points": 3, "daily_limit": 2, "message": "Forum liked reward granted."},
    "daily_login": {"points": 3, "daily_limit": 1, "message": "Daily login reward granted."},
    "streak_7": {"points": 20, "daily_limit": 1, "message": "7-day streak reward granted."},
    "streak_30": {"points": 100, "daily_limit": 1, "message": "30-day streak reward granted."},
}
ZONE_RULES = [
    (Decimal("20.00"), Decimal("-0.30"), 1),
    (Decimal("40.00"), Decimal("0.30"), 2),
    (Decimal("60.00"), Decimal("0.50"), 3),
    (Decimal("80.00"), Decimal("0.75"), 4),
    (Decimal("100.00"), Decimal("1.00"), 5),
]


@dataclass
class SettleResult:
    pet: models.PetInfo
    exp_rate: Decimal
    vitality_zone: int


def q2(value: Union[Decimal, float, int]) -> Decimal:
    return Decimal(value).quantize(DEC2, rounding=ROUND_HALF_UP)


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_zone_for_vitality(vitality: Decimal) -> tuple[int, Decimal]:
    vitality = q2(max(Decimal("0.00"), min(Decimal("100.00"), vitality)))
    for upper_bound, exp_rate, zone in ZONE_RULES:
        if vitality <= upper_bound:
            return zone, exp_rate
    return 5, Decimal("1.00")


def get_boundary_for_zone(zone: int) -> Decimal:
    if zone == 1:
        return Decimal("0.00")
    return {2: Decimal("20.00"), 3: Decimal("40.00"), 4: Decimal("60.00"), 5: Decimal("80.00")}[zone]


def unlock_available_skins(db: Session, user_id: str, pet_type_id: int, level: int) -> None:
    eligible = db.scalars(select(models.Skin).where(models.Skin.pet_type_id == pet_type_id, models.Skin.unlock_level <= level)).all()
    owned = list_owned_skin_ids(db, user_id)
    for skin in eligible:
        if skin.skin_id not in owned:
            db.add(models.UserSkin(user_id=user_id, skin_id=skin.skin_id, acquired_at=utcnow()))
    db.flush()


def ensure_seed_user(db: Session, user_id: str) -> models.PetInfo:
    pet = db.scalar(select(models.PetInfo).where(models.PetInfo.user_id == user_id))
    if pet is not None:
        unlock_available_skins(db, user_id, pet.pet_type_id, pet.level)
        return pet
    pet_type = db.scalar(select(models.PetType).order_by(models.PetType.pet_type_id))
    if pet_type is None:
        raise RuntimeError("Seed data is missing. Initialize the database first.")
    pet = models.PetInfo(user_id=user_id, pet_type_id=pet_type.pet_type_id, name="Fox Buddy", level=1, exp=Decimal("0.00"), vitality=Decimal("60.00"), points=0, current_skin_id=pet_type.default_skin_id, last_updated=utcnow())
    db.add(pet)
    db.flush()
    unlock_available_skins(db, user_id, pet.pet_type_id, pet.level)
    return pet


def get_exp_required_for_level(db: Session, level: int) -> int:
    cfg = db.get(models.LevelConfig, level)
    return int(cfg.exp_required) if cfg is not None else 0


def settle_pet(db: Session, pet: models.PetInfo) -> SettleResult:
    now = utcnow()
    if pet.last_updated >= now:
        unlock_available_skins(db, pet.user_id, pet.pet_type_id, pet.level)
        zone, rate = get_zone_for_vitality(Decimal(pet.vitality))
        return SettleResult(pet=pet, exp_rate=q2(rate), vitality_zone=zone)

    remaining_minutes = Decimal((now - pet.last_updated).total_seconds()) / Decimal("60")
    vitality = Decimal(pet.vitality)
    exp = Decimal(pet.exp)
    level = pet.level

    while remaining_minutes > Decimal("0.000001"):
        zone, exp_rate = get_zone_for_vitality(vitality)
        if vitality <= Decimal("0.00"):
            segment_minutes = remaining_minutes
        else:
            boundary = get_boundary_for_zone(zone)
            if vitality > boundary:
                minutes_to_boundary = (vitality - boundary) / VITALITY_DECAY_PER_MIN
                segment_minutes = min(remaining_minutes, minutes_to_boundary)
            else:
                segment_minutes = remaining_minutes

        vitality_delta = VITALITY_DECAY_PER_MIN * segment_minutes
        vitality = max(Decimal("0.00"), vitality - vitality_delta)
        exp = exp + (exp_rate * segment_minutes)
        if exp < Decimal("0.00"):
            exp = Decimal("0.00")

        while level < MAX_LEVEL:
            needed = Decimal(get_exp_required_for_level(db, level))
            if needed <= 0 or exp < needed:
                break
            exp -= needed
            level += 1

        remaining_minutes -= segment_minutes
        if segment_minutes == Decimal("0"):
            break

    pet.vitality = q2(vitality)
    pet.exp = q2(exp)
    pet.level = level
    pet.last_updated = now
    db.add(pet)
    db.flush()
    unlock_available_skins(db, pet.user_id, pet.pet_type_id, pet.level)

    zone, exp_rate = get_zone_for_vitality(Decimal(pet.vitality))
    return SettleResult(pet=pet, exp_rate=q2(exp_rate), vitality_zone=zone)


def get_or_create_pet(db: Session, user_id: str) -> models.PetInfo:
    pet = ensure_seed_user(db, user_id)
    db.flush()
    return pet


def choose_quote(db: Session, pet: models.PetInfo) -> tuple[models.PetQuote, int]:
    settle = settle_pet(db, pet)
    vitality_value = int(Decimal(settle.pet.vitality).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    quotes = db.scalars(select(models.PetQuote).where(models.PetQuote.pet_type_id == pet.pet_type_id, models.PetQuote.min_vitality <= vitality_value, models.PetQuote.max_vitality >= vitality_value)).all()
    if not quotes:
        fallback = db.scalar(select(models.PetQuote).order_by(func.random()))
        if fallback is None:
            raise RuntimeError("No pet quotes configured.")
        return fallback, settle.vitality_zone
    return random.choice(quotes), settle.vitality_zone


def list_owned_skin_ids(db: Session, user_id: str) -> Set[int]:
    return set(db.scalars(select(models.UserSkin.skin_id).where(models.UserSkin.user_id == user_id)).all())


def today_bounds() -> tuple[datetime, datetime]:
    now = utcnow()
    start = datetime(year=now.year, month=now.month, day=now.day)
    end = start + timedelta(days=1)
    return start, end


def get_task_counts_for_today(db: Session, user_id: str) -> Dict[str, int]:
    start, end = today_bounds()
    rows = db.execute(select(models.TaskRecord.task_type, func.count(models.TaskRecord.record_id)).where(models.TaskRecord.user_id == user_id, models.TaskRecord.completed_at >= start, models.TaskRecord.completed_at < end).group_by(models.TaskRecord.task_type)).all()
    return {task_type: int(count) for task_type, count in rows}


def get_total_points_today(db: Session, user_id: str) -> int:
    start, end = today_bounds()
    total = db.scalar(select(func.coalesce(func.sum(models.TaskRecord.points_earned), 0)).where(models.TaskRecord.user_id == user_id, models.TaskRecord.completed_at >= start, models.TaskRecord.completed_at < end))
    return int(total or 0)
