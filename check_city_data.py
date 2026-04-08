#!/usr/bin/env python
"""检查城市信息数据"""
from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # 检查天气数据
    print("=== 天气数据 ===")
    weathers = db.execute(text("SELECT * FROM city_weather")).fetchall()
    for w in weathers:
        print(f"ID: {w[0]}, Month: {w[1]}, Description: {w[2]}, Icon: {w[3]}")
    
    print("\n=== 景点数据 ===")
    sights = db.execute(text("SELECT * FROM city_sights")).fetchall()
    for s in sights:
        print(f"ID: {s[0]}")
        print(f"  Title: {s[1]}")
        print(f"  Description: {s[2]}")
        print(f"  Icon: {s[3]}")
        print(f"  Image: {s[4]}")
        print(f"  Address: {s[5]}")
        print(f"  Copyright: {s[6]}")
        print()
finally:
    db.close()
