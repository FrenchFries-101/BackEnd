from sqlalchemy import Column, Integer, String, Text
from database import Base


class CityWeather(Base):
    """城市天气信息表"""
    __tablename__ = "city_weather"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="天气ID")
    month = Column(Integer, nullable=False, comment="月份")
    description = Column(String(255), nullable=False, comment="英文天气描述")
    icon = Column(String(100), nullable=False, comment="gif或icon文件名")


class CitySights(Base):
    """城市景点信息表"""
    __tablename__ = "city_sights"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="景点ID")
    title = Column(String(100), nullable=False, comment="景点名称英文")
    description = Column(String(255), nullable=False, comment="描述英文")
    icon = Column(String(100), nullable=True, comment="小gif icon文件名")
    image = Column(String(255), nullable=True, comment="图片文件路径")
    address = Column(String(255), nullable=True, comment="地址英文")
    copyright = Column(String(255), nullable=True, comment="图片版权网址")
