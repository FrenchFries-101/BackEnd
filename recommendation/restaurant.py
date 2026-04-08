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
    """随机推荐餐馆"""
    # 构建查询条件
    conditions = []
    params = {}
    
    if location:
        conditions.append("location = :location")
        params["location"] = location
    
    if cuisine:
        conditions.append("cuisine = :cuisine")
        params["cuisine"] = cuisine
    
    if spice_level:
        conditions.append("spice_level = :spice_level")
        params["spice_level"] = spice_level
    
    # 构建 WHERE 子句
    where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
    
    # 执行随机查询
    query = f"SELECT id, name, location, cuisine, spice_level FROM restaurant{where_clause} ORDER BY RAND() LIMIT 1"
    
    result = db.execute(text(query), params).fetchone()
    
    if result is None:
        # 如果筛选结果为空，返回数据库中的任意一条
        result = db.execute(
            text("SELECT id, name, location, cuisine, spice_level FROM restaurant ORDER BY RAND() LIMIT 1")
        ).fetchone()
        
        if result is None:
            raise HTTPException(status_code=404, detail="No restaurants found in database")
    
    return RestaurantResponse(
        id=result[0],
        name=result[1],
        location=result[2],
        cuisine=result[3],
        spice_level=result[4]
    )


@router.get("/refresh", response_model=RestaurantResponse)
def refresh_recommendation(
    location: str = Query(None, description="地点筛选"),
    cuisine: str = Query(None, description="风味筛选"),
    spice_level: str = Query(None, description="辣度筛选"),
    db: Session = Depends(get_db)
) -> RestaurantResponse:
    """刷新推荐（与 recommend 相同）"""
    return recommend_restaurant(location, cuisine, spice_level, db)


def init_restaurant_db():
    """初始化美食推荐数据库表"""
    from database import engine
    Restaurant.metadata.create_all(bind=engine)
