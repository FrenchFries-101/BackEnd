from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from recommendation.models import Restaurant, FILTER_OPTIONS
from recommendation.schemas import FiltersResponse, RestaurantResponse
from database import get_db

router = APIRouter(prefix="/api/restaurant", tags=["Restaurant"])


@router.get("/filters", response_model=FiltersResponse)
def get_filters() -> FiltersResponse:
    """获取所有筛选条件"""
    return FiltersResponse(**FILTER_OPTIONS)


@router.get("/recommend", response_model=RestaurantResponse)
def recommend_restaurant(
    location: str = Query(None, description="地点筛选"),
    cuisine: str = Query(None, description="风味筛选"),
    spice_level: str = Query(None, description="辣度筛选"),
    db: Session = Depends(get_db)
) -> RestaurantResponse:
    """随机推荐餐馆 - 使用ORM确保筛选条件严格生效"""

    from sqlalchemy import func

    query = db.query(Restaurant)

    if location:
        query = query.filter(Restaurant.location == location)

    if cuisine:
        query = query.filter(Restaurant.cuisine == cuisine)

    if spice_level:
        query = query.filter(Restaurant.spice_level == spice_level)

    result = query.order_by(func.rand()).first()

    if result is None:
        error_msg = "No restaurants found"
        filters = []
        if location:
            filters.append(f"location={location}")
        if cuisine:
            filters.append(f"cuisine={cuisine}")
        if spice_level:
            filters.append(f"spice_level={spice_level}")
        if filters:
            error_msg = f"No restaurants found with filters: {', '.join(filters)}"
        raise HTTPException(status_code=404, detail=error_msg)

    return RestaurantResponse(
        id=result.id,
        name=result.name,
        location=result.location,
        cuisine=result.cuisine,
        spice_level=result.spice_level
    )


@router.get("/refresh", response_model=RestaurantResponse)
def refresh_recommendation(
    location: str = Query(None, description="地点筛选"),
    cuisine: str = Query(None, description="风味筛选"),
    spice_level: str = Query(None, description="辣度筛选"),
    db: Session = Depends(get_db)
) -> RestaurantResponse:
    """刷新推荐（与 recommend 相同）"""
    return recommend_restaurant(
        location=location,
        cuisine=cuisine,
        spice_level=spice_level,
        db=db
    )


def init_restaurant_db():
    """初始化美食推荐数据库表"""
    from database import engine
    Restaurant.metadata.create_all(bind=engine)
