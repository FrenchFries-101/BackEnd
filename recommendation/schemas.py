from pydantic import BaseModel
from typing import List, Optional


class FilterOption(BaseModel):
    """筛选选项"""
    value: str
    label: str
    display: str


class FiltersResponse(BaseModel):
    """筛选条件响应"""
    locations: List[FilterOption]
    cuisines: List[FilterOption]
    spice_levels: List[FilterOption]


class RestaurantResponse(BaseModel):
    """餐馆推荐响应"""
    id: int
    name: str
    location: str
    cuisine: str
    spice_level: str


class RecommendRequest(BaseModel):
    """推荐请求参数"""
    location: Optional[str] = None
    cuisine: Optional[str] = None
    spice_level: Optional[str] = None
