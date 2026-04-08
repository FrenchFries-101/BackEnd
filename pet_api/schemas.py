from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    success: bool
    message: str


class PetStatusResponse(BaseModel):
    pet_id: int
    name: str
    pet_type_id: int
    pet_type_name: str
    level: int
    exp: Decimal
    exp_required: int
    vitality: Decimal
    vitality_zone: int
    points: int
    current_skin_id: Optional[int] = None
    exp_rate: Decimal
    last_updated: datetime


class LevelConfigResponse(BaseModel):
    level: int
    exp_required: int
    unlock_skin_id: Optional[int] = None


class SkinSimpleResponse(BaseModel):
    skin_id: int
    name: str
    gif_url: str


class ModifyNameRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=50)


class QuoteResponse(BaseModel):
    quote_id: int
    content: str
    vitality_zone: int


class SkinResponse(BaseModel):
    skin_id: int
    name: str
    description: Optional[str] = None
    gif_url: str
    unlock_level: int
    owned: bool
    current: bool


class SetCurrentSkinRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    skin_id: int


class ServiceCategoryResponse(BaseModel):
    category_id: int
    name: str


class ServiceResponse(BaseModel):
    service_id: int
    name: str
    vitality_effect: Decimal
    points_cost: int
    gif_url: Optional[str] = None
    cooldown_seconds: int


class ApplyServiceRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    service_id: int


class ApplyServiceResponse(BaseModel):
    success: bool
    new_vitality: Optional[Decimal] = None
    new_points: Optional[int] = None
    vitality_gained: Optional[Decimal] = None
    points_spent: Optional[int] = None
    message: Optional[str] = None


class CompleteTaskRequest(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    task_type: str = Field(..., min_length=1, max_length=50)


class CompleteTaskResponse(BaseModel):
    success: bool
    points_earned: int
    new_points: Optional[int] = None
    daily_limit_reached: bool
    message: str


class DailyTaskProgressItem(BaseModel):
    task_type: str
    completed: int
    daily_limit: int


class DailyProgressResponse(BaseModel):
    date: date
    tasks: List[DailyTaskProgressItem]
    total_earned_today: int
    daily_cap: int
    remaining_cap: int


class PetTypeResponse(BaseModel):
    pet_type_id: int
    name: str
    description: Optional[str] = None
    default_skin_id: Optional[int] = None


class HealthResponse(BaseModel):
    ok: bool
    database_url: str


class PetNameResponse(BaseModel):
    pet_id: int
    name: str
