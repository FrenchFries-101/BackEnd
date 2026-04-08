from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List

from recommendation.changsha_models import CityWeather, CitySights
from recommendation.changsha_schemas import WeatherResponse, SightResponse
from database import get_db

router = APIRouter(prefix="/api/city", tags=["City Info"])


@router.get("/weather", response_model=WeatherResponse)
def get_weather(
    month: int = Query(None, description="月份，默认返回当前月份"),
    db: Session = Depends(get_db)
) -> WeatherResponse:
    """获取城市天气信息"""
    # 如果没有指定月份，使用当前月份
    if month is None:
        month = datetime.now().month
    
    # 查询指定月份的天气信息
    result = db.execute(
        text("SELECT month, description, icon FROM city_weather WHERE month = :month"),
        {"month": month}
    ).fetchone()
    
    if result is None:
        # 如果没有找到，返回默认的3月数据
        result = db.execute(
            text("SELECT month, description, icon FROM city_weather ORDER BY month LIMIT 1")
        ).fetchone()
        if result is None:
            raise ValueError("No weather data available")
    
    return WeatherResponse(
        month=result[0],
        description=result[1],
        icon_url=result[2]
    )


@router.get("/sights", response_model=List[SightResponse])
def get_sights(
    limit: int = Query(3, ge=1, le=100, description="返回景点数量，默认3条"),
    db: Session = Depends(get_db)
) -> List[SightResponse]:
    """获取城市景点信息"""
    # 查询景点信息
    results = db.execute(
        text("SELECT title, description, icon, image, address, copyright FROM city_sights LIMIT :limit"),
        {"limit": limit}
    ).fetchall()
    
    sights = []
    for row in results:
        sights.append(SightResponse(
            title=row[0],
            description=row[1],
            icon_url=row[2],
            image_url=row[3],
            address=row[4],
            copyright=row[5]
        ))
    
    return sights


def init_city_db():
    """初始化城市信息数据库表"""
    from database import engine
    CityWeather.metadata.create_all(bind=engine)
    CitySights.metadata.create_all(bind=engine)
