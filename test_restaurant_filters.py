from database import SessionLocal, engine
from sqlalchemy import text
from recommendation.models import Restaurant

print("=== 检查数据库中的餐厅数据 ===\n")

db = SessionLocal()

# 检查所有餐厅
print("1. 所有餐厅统计:")
all_restaurants = db.execute(text("SELECT COUNT(*) FROM restaurant")).scalar()
print(f"   总数: {all_restaurants}\n")

# 检查Houhu的餐厅
print("2. Houhu地区的餐厅:")
houhu_restaurants = db.execute(text("SELECT name, location, cuisine FROM restaurant WHERE location = 'Houhu'")).fetchall()
print(f"   数量: {len(houhu_restaurants)}")
for row in houhu_restaurants:
    print(f"   - {row[0]} | {row[1]} | {row[2]}")
print()

# 检查Western的餐厅
print("3. Western菜系的餐厅:")
western_restaurants = db.execute(text("SELECT name, location, cuisine FROM restaurant WHERE cuisine = 'Western'")).fetchall()
print(f"   数量: {len(western_restaurants)}")
for row in western_restaurants:
    print(f"   - {row[0]} | {row[1]} | {row[2]}")
print()

# 检查Houhu + Western组合
print("4. Houhu + Western组合:")
houhu_western = db.execute(text("SELECT name, location, cuisine FROM restaurant WHERE location = 'Houhu' AND cuisine = 'Western'")).fetchall()
print(f"   数量: {len(houhu_western)}")
if houhu_western:
    for row in houhu_western:
        print(f"   - {row[0]} | {row[1]} | {row[2]}")
else:
    print("   ❌ 没有找到符合 Houhu + Western 的餐厅！")
    print("\n   这就是问题所在：当没有符合条件的餐厅时，")
    print("   后端返回了一个随机的餐厅作为fallback！")
print()

# 显示所有location和cuisine组合
print("5. 所有location和cuisine组合统计:")
combinations = db.execute(text("""
    SELECT location, cuisine, COUNT(*) as count
    FROM restaurant
    GROUP BY location, cuisine
    ORDER BY location, cuisine
""")).fetchall()
for row in combinations:
    print(f"   {row[0]} + {row[1]}: {row[2]}家")
