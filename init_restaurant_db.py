#!/usr/bin/env python
"""
初始化美食推荐数据库表和种子数据
"""
from database import engine, SessionLocal
from recommendation.models import Restaurant
from recommendation.restaurant import init_restaurant_db
from recommendation.seed import seed_restaurant_data


def init_database():
    """初始化数据库表和种子数据"""
    print("开始初始化美食推荐数据库...")
    
    # 1. 创建数据库表
    print("\n1. 创建数据库表...")
    init_restaurant_db()
    print("✅ 数据库表创建完成")
    
    # 2. 初始化种子数据
    print("\n2. 初始化种子数据...")
    db = SessionLocal()
    try:
        seed_restaurant_data(db)
        print("✅ 种子数据初始化完成")
        
        # 显示初始化的数据
        print(f"\n3. 数据统计:")
        total = db.query(Restaurant).count()
        print(f"   总餐馆数量: {total}")
        
        # 按地点统计
        from sqlalchemy import func
        locations = db.query(
            Restaurant.location, 
            func.count(Restaurant.id)
        ).group_by(Restaurant.location).all()
        print(f"   按地点分布:")
        for loc, count in locations:
            print(f"     - {loc}: {count} 家")
        
        # 按风味统计
        cuisines = db.query(
            Restaurant.cuisine, 
            func.count(Restaurant.id)
        ).group_by(Restaurant.cuisine).all()
        print(f"   按风味分布:")
        for cuisine, count in cuisines:
            print(f"     - {cuisine}: {count} 家")
            
    except Exception as e:
        print(f"❌ 种子数据初始化失败: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    print("\n✅ 数据库初始化完成！")


if __name__ == "__main__":
    init_database()
