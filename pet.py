from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from pet_api import models, schemas
from pet_api.database import Base, DATABASE_URL, engine, get_db
from pet_api.seed import seed_data
from pet_api.services.pet_logic import (
    DAILY_POINTS_CAP,
    TASK_CONFIG,
    choose_quote,
    get_exp_required_for_level,
    get_or_create_pet,
    get_task_counts_for_today,
    get_total_points_today,
    list_owned_skin_ids,
    q2,
    settle_pet,
    today_bounds,
    utcnow,
)

# ── t_user 积分操作（以 t_user.points 为准） ──

def get_t_user_points(db: Session, user_id: str) -> int:
    # Debug: 添加调试日志
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.info(f"[DEBUG] get_t_user_points - input user_id={user_id}, type={type(user_id)}")
    logging.info(f"[DEBUG] query: SELECT points FROM t_user WHERE user_id = {user_id} AND is_delete = 0")
    
    row = db.execute(
        text("SELECT points FROM t_user WHERE user_id = :uid AND is_delete = 0"),
        {"uid": int(user_id)},
    ).fetchone()
    
    logging.info(f"[DEBUG] query result row={row}")
    
    return int(row[0]) if row else 0


def deduct_t_user_points(db: Session, user_id: str, amount: int) -> int:
    db.execute(
        text("UPDATE t_user SET points = points - :amt WHERE user_id = :uid AND is_delete = 0"),
        {"amt": amount, "uid": int(user_id)},
    )
    return get_t_user_points(db, user_id)


def add_t_user_points(db: Session, user_id: str, amount: int) -> int:
    db.execute(
        text("UPDATE t_user SET points = points + :amt WHERE user_id = :uid AND is_delete = 0"),
        {"amt": amount, "uid": int(user_id)},
    )
    return get_t_user_points(db, user_id)

router = APIRouter(prefix="/pet_module", tags=["Pet"])


def init_pet_db() -> None:
    Base.metadata.create_all(bind=engine)
    with Session(engine) as db:
        seed_data(db)
        db.commit()


@router.get("/health", response_model=schemas.HealthResponse)
def health() -> schemas.HealthResponse:
    return schemas.HealthResponse(ok=True, database_url=DATABASE_URL)


@router.get("/pet/status", response_model=schemas.PetStatusResponse)
def get_pet_status(user_id: str = Query(...), db: Session = Depends(get_db)) -> schemas.PetStatusResponse:
    pet = get_or_create_pet(db, user_id)
    result = settle_pet(db, pet)
    db.commit()
    return schemas.PetStatusResponse(
        pet_id=result.pet.pet_id,
        name=result.pet.name,
        pet_type_id=result.pet.pet_type_id,
        pet_type_name=result.pet.pet_type.name,
        level=result.pet.level,
        exp=q2(Decimal(result.pet.exp)),
        exp_required=get_exp_required_for_level(db, result.pet.level),
        vitality=q2(Decimal(result.pet.vitality)),
        vitality_zone=result.vitality_zone,
        points=get_t_user_points(db, result.pet.user_id),
        current_skin_id=result.pet.current_skin_id,
        exp_rate=result.exp_rate,
        last_updated=result.pet.last_updated,
    )


@router.get("/pet/level_config", response_model=list[schemas.LevelConfigResponse])
def get_level_config(db: Session = Depends(get_db)) -> list[schemas.LevelConfigResponse]:
    rows = db.scalars(select(models.LevelConfig).order_by(models.LevelConfig.level)).all()
    return [
        schemas.LevelConfigResponse(level=row.level, exp_required=row.exp_required, unlock_skin_id=row.unlock_skin_id)
        for row in rows
    ]


@router.get("/pet/types", response_model=list[schemas.PetTypeResponse])
def pet_types(db: Session = Depends(get_db)) -> list[schemas.PetTypeResponse]:
    rows = db.scalars(select(models.PetType).order_by(models.PetType.pet_type_id)).all()
    return [
        schemas.PetTypeResponse(
            pet_type_id=row.pet_type_id,
            name=row.name,
            description=row.description,
            default_skin_id=row.default_skin_id,
        )
        for row in rows
    ]


@router.get("/pet/quote", response_model=schemas.QuoteResponse)
def get_quote(user_id: str = Query(...), db: Session = Depends(get_db)) -> schemas.QuoteResponse:
    pet = get_or_create_pet(db, user_id)
    quote, vitality_zone = choose_quote(db, pet)
    db.commit()
    return schemas.QuoteResponse(quote_id=quote.quote_id, content=quote.content, vitality_zone=vitality_zone)


@router.post("/pet/modify_name", response_model=schemas.MessageResponse)
def modify_name(payload: schemas.ModifyNameRequest, db: Session = Depends(get_db)) -> schemas.MessageResponse:
    pet = get_or_create_pet(db, payload.user_id)
    pet.name = payload.name.strip()
    db.add(pet)
    db.commit()
    return schemas.MessageResponse(success=True, message="Pet name updated successfully.")


@router.get("/pet/current_skin", response_model=schemas.SkinSimpleResponse)
def get_current_skin(user_id: str = Query(...), db: Session = Depends(get_db)) -> schemas.SkinSimpleResponse:
    pet = get_or_create_pet(db, user_id)
    settle_pet(db, pet)
    db.commit()
    skin = db.get(models.Skin, pet.current_skin_id)
    if skin is None:
        raise HTTPException(status_code=404, detail="Current skin not found")
    return schemas.SkinSimpleResponse(skin_id=skin.skin_id, name=skin.name, gif_url=skin.gif_url)


@router.get("/pet/skins", response_model=list[schemas.SkinResponse])
def get_skins(user_id: str = Query(...), db: Session = Depends(get_db)) -> list[schemas.SkinResponse]:
    pet = get_or_create_pet(db, user_id)
    settle_pet(db, pet)
    db.commit()
    rows = db.scalars(
        select(models.Skin).where(models.Skin.pet_type_id == pet.pet_type_id).order_by(models.Skin.skin_id)
    ).all()
    owned = list_owned_skin_ids(db, user_id)
    return [
        schemas.SkinResponse(
            skin_id=skin.skin_id,
            name=skin.name,
            description=skin.description,
            gif_url=skin.gif_url,
            unlock_level=skin.unlock_level,
            owned=skin.skin_id in owned,
            current=skin.skin_id == pet.current_skin_id,
        )
        for skin in rows
    ]


@router.post("/pet/current_skin", response_model=schemas.MessageResponse)
def set_current_skin(payload: schemas.SetCurrentSkinRequest, db: Session = Depends(get_db)) -> schemas.MessageResponse:
    pet = get_or_create_pet(db, payload.user_id)
    settle_pet(db, pet)
    owned = list_owned_skin_ids(db, payload.user_id)
    if payload.skin_id not in owned:
        db.commit()
        return schemas.MessageResponse(success=False, message="The selected skin is not unlocked yet.")
    skin = db.get(models.Skin, payload.skin_id)
    if skin is None or skin.pet_type_id != pet.pet_type_id:
        raise HTTPException(status_code=404, detail="Skin not found for the current pet type")
    pet.current_skin_id = payload.skin_id
    db.add(pet)
    db.commit()
    return schemas.MessageResponse(success=True, message="Skin switched successfully.")


@router.get("/pet/service_categories", response_model=list[schemas.ServiceCategoryResponse])
def get_service_categories(db: Session = Depends(get_db)) -> list[schemas.ServiceCategoryResponse]:
    rows = db.scalars(select(models.ServiceCategory).order_by(models.ServiceCategory.category_id)).all()
    return [schemas.ServiceCategoryResponse(category_id=row.category_id, name=row.name) for row in rows]


@router.get("/pet/services", response_model=list[schemas.ServiceResponse])
def get_services(category_id: int = Query(...), db: Session = Depends(get_db)) -> list[schemas.ServiceResponse]:
    rows = db.scalars(
        select(models.Service)
        .where(models.Service.category_id == category_id)
        .order_by(models.Service.service_id)
    ).all()
    return [
        schemas.ServiceResponse(
            service_id=row.service_id,
            name=row.name,
            vitality_effect=q2(Decimal(row.vitality_effect)),
            points_cost=row.points_cost,
            gif_url=row.gif_url,
            cooldown_seconds=row.cooldown_seconds,
        )
        for row in rows
    ]


@router.post("/pet/apply_service", response_model=schemas.ApplyServiceResponse)
def apply_service(payload: schemas.ApplyServiceRequest, db: Session = Depends(get_db)) -> schemas.ApplyServiceResponse:
    pet = get_or_create_pet(db, payload.user_id)
    settle_pet(db, pet)
    service = db.get(models.Service, payload.service_id)
    if service is None:
        raise HTTPException(status_code=404, detail="Service not found")

    user_points = get_t_user_points(db, payload.user_id)

    # Debug: 添加调试日志
    import logging
    logging.basicConfig(level=logging.INFO)
    logging.info(f"[DEBUG] apply_service - user_id={payload.user_id}, type={type(payload.user_id)}")
    logging.info(f"[DEBUG] user_points={user_points}, service.points_cost={service.points_cost}")

    if user_points < service.points_cost:
        db.add(models.UserServiceRecord(
            user_id=payload.user_id,
            service_id=payload.service_id,
            applied_at=utcnow(),
            success=False,
            effect_vitality=Decimal("0.00"),
            effect_points=0,
        ))
        db.commit()
        return schemas.ApplyServiceResponse(success=False, message="Insufficient points.")

    last_success = db.scalar(
        select(models.UserServiceRecord)
        .where(
            models.UserServiceRecord.user_id == payload.user_id,
            models.UserServiceRecord.service_id == payload.service_id,
            models.UserServiceRecord.success.is_(True),
        )
        .order_by(models.UserServiceRecord.applied_at.desc())
        .limit(1)
    )
    if last_success is not None:
        elapsed = utcnow() - last_success.applied_at
        remaining = service.cooldown_seconds - int(elapsed.total_seconds())
        if remaining > 0:
            db.add(models.UserServiceRecord(
                user_id=payload.user_id,
                service_id=payload.service_id,
                applied_at=utcnow(),
                success=False,
                effect_vitality=Decimal("0.00"),
                effect_points=0,
            ))
            db.commit()
            return schemas.ApplyServiceResponse(success=False, message=f"Service is cooling down, wait {remaining} seconds.")

    vitality_before = Decimal(pet.vitality)
    new_points = deduct_t_user_points(db, payload.user_id, service.points_cost)
    pet.vitality = q2(min(Decimal("100.00"), Decimal(pet.vitality) + Decimal(service.vitality_effect)))
    db.add(pet)
    db.add(models.UserServiceRecord(
        user_id=payload.user_id,
        service_id=payload.service_id,
        applied_at=utcnow(),
        success=True,
        effect_vitality=q2(Decimal(pet.vitality) - vitality_before),
        effect_points=-service.points_cost,
    ))
    db.commit()
    return schemas.ApplyServiceResponse(
        success=True,
        new_vitality=q2(Decimal(pet.vitality)),
        new_points=new_points,
        vitality_gained=q2(Decimal(pet.vitality) - vitality_before),
        points_spent=service.points_cost,
        message="Service applied successfully.",
    )


@router.post("/task/complete", response_model=schemas.CompleteTaskResponse)
def complete_task(payload: schemas.CompleteTaskRequest, db: Session = Depends(get_db)) -> schemas.CompleteTaskResponse:
    task_cfg = TASK_CONFIG.get(payload.task_type)
    if task_cfg is None:
        raise HTTPException(status_code=400, detail="Unsupported task type")

    pet = get_or_create_pet(db, payload.user_id)
    settle_pet(db, pet)
    counts = get_task_counts_for_today(db, payload.user_id)
    current_count = counts.get(payload.task_type, 0)
    if current_count >= task_cfg["daily_limit"]:
        db.commit()
        return schemas.CompleteTaskResponse(
            success=False,
            points_earned=0,
            new_points=get_t_user_points(db, payload.user_id),
            daily_limit_reached=True,
            message="Daily limit reached for this task type.",
        )

    total_today = get_total_points_today(db, payload.user_id)
    reward = task_cfg["points"]
    if total_today + reward > DAILY_POINTS_CAP:
        db.commit()
        return schemas.CompleteTaskResponse(
            success=False,
            points_earned=0,
            new_points=get_t_user_points(db, payload.user_id),
            daily_limit_reached=True,
            message="Daily point cap reached.",
        )

    new_points = add_t_user_points(db, payload.user_id, reward)
    db.add(pet)
    db.add(models.TaskRecord(
        user_id=payload.user_id,
        task_type=payload.task_type,
        completed_at=utcnow(),
        points_earned=reward,
    ))
    db.commit()
    return schemas.CompleteTaskResponse(
        success=True,
        points_earned=reward,
        new_points=new_points,
        daily_limit_reached=False,
        message=task_cfg["message"],
    )


@router.get("/task/daily_progress", response_model=schemas.DailyProgressResponse)
def daily_progress(user_id: str = Query(...), db: Session = Depends(get_db)) -> schemas.DailyProgressResponse:
    get_or_create_pet(db, user_id)
    counts = get_task_counts_for_today(db, user_id)
    total = get_total_points_today(db, user_id)
    db.commit()
    tasks = [
        schemas.DailyTaskProgressItem(
            task_type=task_type,
            completed=counts.get(task_type, 0),
            daily_limit=cfg["daily_limit"],
        )
        for task_type, cfg in TASK_CONFIG.items()
    ]
    start, _ = today_bounds()
    return schemas.DailyProgressResponse(
        date=start.date(),
        tasks=tasks,
        total_earned_today=total,
        daily_cap=DAILY_POINTS_CAP,
        remaining_cap=max(0, DAILY_POINTS_CAP - total),
    )
