from pydantic import BaseModel
from typing import Optional, List


class WeatherResponse(BaseModel):
    """天气信息响应"""
    month: int
    description: str
    icon_url: str


class SightResponse(BaseModel):
    """景点信息响应"""
    title: str
    description: str
    icon_url: Optional[str]
    image_url: Optional[str]
    address: Optional[str]
    copyright: Optional[str]
