#!/usr/bin/env python
"""
初始化城市信息数据库表和种子数据
"""
from database import engine, SessionLocal
from recommendation.changsha_models import CityWeather, CitySights
from recommendation.changsha import init_city_db
from recommendation.changsha_seed import seed_city_data


def init_database():
    """初始化数据库表和种子数据"""
    print("开始初始化城市信息数据库...")
    
    # 1. 创建数据库表
    print("\n1. 创建数据库表...")
    init_city_db()
    print("✅ 数据库表创建完成")
    
    # 2. 初始化种子数据
    print("\n2. 初始化种子数据...")
    db = SessionLocal()
    try:
        seed_city_data(db)
        print("✅ 种子数据初始化完成")
        
        # 显示初始化的数据
        print(f"\n3. 数据统计:")
        weather_count = db.query(CityWeather).count()
        sights_count = db.query(CitySights).count()
        print(f"   天气数据: {weather_count} 条")
        print(f"   景点数据: {sights_count} 条")
        
        # 显示天气数据
        print(f"\n4. 天气数据:")
        weathers = db.query(CityWeather).order_by(CityWeather.month).all()
        for w in weathers:
            print(f"   - {w.month}月: {w.description}")
        
        # 显示景点数据
        print(f"\n5. 景点数据:")
        sights = db.query(CitySights).all()
        for s in sights:
            print(f"   - {s.title}: {s.description}")
            
    except Exception as e:
        print(f"❌ 种子数据初始化失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    print("\n✅ 数据库初始化完成！")


if __name__ == "__main__":
    init_database()
