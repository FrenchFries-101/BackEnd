from sqlalchemy.orm import Session
from recommendation.models import Restaurant


def seed_restaurant_data(db: Session) -> None:
    """初始化餐馆测试数据"""
    # 检查是否已有数据
    existing = db.query(Restaurant).count()
    if existing > 0:
        return
    
    # 初始化测试数据
    restaurants = [
        # 后湖小区 - 中餐
        Restaurant(name="遇见牛肉钵火锅", location="Houhu", cuisine="Chinese", spice_level="Spicy"),
        Restaurant(name="老长沙油炸社", location="Houhu", cuisine="Chinese", spice_level="Mild"),
        Restaurant(name="湘西土菜馆", location="Houhu", cuisine="Chinese", spice_level="Spicy"),
        Restaurant(name="家常小炒", location="Houhu", cuisine="Chinese", spice_level="None"),
        
        # 后湖小区 - 快餐
        Restaurant(name="杨国福麻辣烫", location="Houhu", cuisine="FastFood", spice_level="Mild"),
        Restaurant(name="台湾卤肉饭", location="Houhu", cuisine="FastFood", spice_level="None"),
        
        # 麓山南路 - 中餐
        Restaurant(name="麓山食堂", location="Lushan", cuisine="Chinese", spice_level="Mild"),
        Restaurant(name="臭豆腐店", location="Lushan", cuisine="Chinese", spice_level="Spicy"),
        
        # 麓山南路 - 西餐
        Restaurant(name="星巴克咖啡", location="Lushan", cuisine="Western", spice_level="None"),
        Restaurant(name="必胜客", location="Lushan", cuisine="Western", spice_level="None"),
        
        # 麓山南路 - 日料
        Restaurant(name="寿司郎", location="Lushan", cuisine="Japanese", spice_level="None"),
        Restaurant(name="日式拉面馆", location="Lushan", cuisine="Japanese", spice_level="Mild"),
        
        # 麓山南路 - 韩餐
        Restaurant(name="首尔炸鸡", location="Lushan", cuisine="Korean", spice_level="Mild"),
        Restaurant(name="韩式烤肉", location="Lushan", cuisine="Korean", spice_level="Spicy"),
        
        # 学校食堂 - 中餐
        Restaurant(name="第一食堂", location="Canteen", cuisine="Chinese", spice_level="Mild"),
        Restaurant(name="第二食堂", location="Canteen", cuisine="Chinese", spice_level="Spicy"),
        Restaurant(name="清真食堂", location="Canteen", cuisine="Chinese", spice_level="None"),
        
        # 学校食堂 - 快餐
        Restaurant(name="风味小吃城", location="Canteen", cuisine="FastFood", spice_level="None"),
        
        # 天马小区 - 中餐
        Restaurant(name="天马农家菜", location="Tianma", cuisine="Chinese", spice_level="Mild"),
        Restaurant(name="湘菜馆", location="Tianma", cuisine="Chinese", spice_level="Spicy"),
        
        # 天马小区 - 西餐
        Restaurant(name="麦当劳", location="Tianma", cuisine="Western", spice_level="None"),
        Restaurant(name="肯德基", location="Tianma", cuisine="Western", spice_level="None"),
        
        # 天马小区 - 日料
        Restaurant(name="回转寿司", location="Tianma", cuisine="Japanese", spice_level="None"),
        
        # 天马小区 - 韩餐
        Restaurant(name="石锅拌饭", location="Tianma", cuisine="Korean", spice_level="Mild"),
        
        # 天马小区 - 其他
        Restaurant(name="印度咖喱", location="Tianma", cuisine="Others", spice_level="Spicy"),
        Restaurant(name="泰式料理", location="Tianma", cuisine="Others", spice_level="Spicy"),
    ]
    
    db.add_all(restaurants)
    db.commit()
    print(f"Initialized {len(restaurants)} restaurant records")
