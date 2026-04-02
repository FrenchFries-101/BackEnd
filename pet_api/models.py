from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class PetType(Base):
    __tablename__ = "pet_types"

    pet_type_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_skin_id: Mapped[int | None] = mapped_column(ForeignKey("skins.skin_id"), nullable=True)


class PetInfo(Base):
    __tablename__ = "pet_info"

    pet_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    pet_type_id: Mapped[int] = mapped_column(ForeignKey("pet_types.pet_type_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    exp: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False, default=Decimal("0.00"))
    vitality: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("60.00"))
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    current_skin_id: Mapped[int | None] = mapped_column(ForeignKey("skins.skin_id"), nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    pet_type: Mapped[PetType] = relationship("PetType")
    current_skin: Mapped[Skin | None] = relationship("Skin", foreign_keys=[current_skin_id])


class LevelConfig(Base):
    __tablename__ = "level_config"

    level: Mapped[int] = mapped_column(Integer, primary_key=True)
    exp_required: Mapped[int] = mapped_column(Integer, nullable=False)
    unlock_skin_id: Mapped[int | None] = mapped_column(ForeignKey("skins.skin_id"), nullable=True)


class Skin(Base):
    __tablename__ = "skins"

    skin_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_type_id: Mapped[int] = mapped_column(ForeignKey("pet_types.pet_type_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    gif_url: Mapped[str] = mapped_column(String(255), nullable=False)
    unlock_level: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class UserSkin(Base):
    __tablename__ = "user_skins"
    __table_args__ = (UniqueConstraint("user_id", "skin_id", name="uq_user_skin"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    skin_id: Mapped[int] = mapped_column(ForeignKey("skins.skin_id"), nullable=False)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)


class PetQuote(Base):
    __tablename__ = "pet_quotes"

    quote_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    pet_type_id: Mapped[int] = mapped_column(ForeignKey("pet_types.pet_type_id"), nullable=False)
    min_vitality: Mapped[int] = mapped_column(Integer, nullable=False)
    max_vitality: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    category_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


class Service(Base):
    __tablename__ = "services"

    service_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("service_categories.category_id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    vitality_effect: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    points_cost: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gif_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class UserServiceRecord(Base):
    __tablename__ = "user_service_records"

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.service_id"), nullable=False)
    applied_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    effect_vitality: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    effect_points: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TaskRecord(Base):
    __tablename__ = "task_records"

    record_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    points_earned: Mapped[int] = mapped_column(Integer, nullable=False)
