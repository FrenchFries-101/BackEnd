from sqlalchemy import Column, Integer, String
from database import Base


class Restaurant(Base):
    """美食推荐表"""
    __tablename__ = "restaurant"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="餐馆ID")
    name = Column(String(100), nullable=False, comment="中文餐馆名字")
    location = Column(String(50), nullable=False, comment="地点英文值")
    cuisine = Column(String(50), nullable=False, comment="风味英文值")
    spice_level = Column(String(10), nullable=False, comment="辣度英文值")


# 筛选选项映射配置
FILTER_OPTIONS = {
    "locations": [
        {"value": "Houhu", "label": "后湖小区", "display": "Houhu District"},
        {"value": "Lushan", "label": "麓山南路", "display": "Lushan South Rd"},
        {"value": "Canteen", "label": "学校食堂", "display": "School Canteen"},
        {"value": "Tianma", "label": "天马小区", "display": "Tianma District"},
    ],
    "cuisines": [
        {"value": "Chinese", "label": "中餐", "display": "Chinese"},
        {"value": "Western", "label": "西餐", "display": "Western"},
        {"value": "Japanese", "label": "日料", "display": "Japanese"},
        {"value": "Korean", "label": "韩餐", "display": "Korean"},
        {"value": "FastFood", "label": "快餐", "display": "Fast Food"},
        {"value": "Others", "label": "其他", "display": "Others"},
    ],
    "spice_levels": [
        {"value": "None", "label": "不辣", "display": "None"},
        {"value": "Mild", "label": "微辣", "display": "Mild"},
        {"value": "Spicy", "label": "辣", "display": "Spicy"},
    ],
}
