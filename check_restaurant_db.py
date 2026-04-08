import pymysql

# 数据库连接配置
config = {
    'host': '124.223.33.28',
    'port': 3306,
    'user': 'cardData',
    'password': 'zxN8TNNP4Ghf4Ksb',
    'database': 'carddata',
    'charset': 'utf8mb4'
}

print("=== 检查数据库中的餐厅数据 ===\n")

try:
    conn = pymysql.connect(**config)
    cursor = conn.cursor()

    # 检查所有餐厅
    print("1. 所有餐厅统计:")
    cursor.execute("SELECT COUNT(*) FROM restaurant")
    count = cursor.fetchone()[0]
    print(f"   总数: {count}\n")

    # 检查Houhu的餐厅
    print("2. Houhu地区的餐厅:")
    cursor.execute("SELECT name, location, cuisine FROM restaurant WHERE location = 'Houhu'")
    houhu = cursor.fetchall()
    print(f"   数量: {len(houhu)}")
    for row in houhu:
        print(f"   - {row[0]} | {row[1]} | {row[2]}")
    print()

    # 检查Western的餐厅
    print("3. Western菜系的餐厅:")
    cursor.execute("SELECT name, location, cuisine FROM restaurant WHERE cuisine = 'Western'")
    western = cursor.fetchall()
    print(f"   数量: {len(western)}")
    for row in western:
        print(f"   - {row[0]} | {row[1]} | {row[2]}")
    print()

    # 检查Houhu + Western组合
    print("4. Houhu + Western组合:")
    cursor.execute("SELECT name, location, cuisine FROM restaurant WHERE location = 'Houhu' AND cuisine = 'Western'")
    houhu_western = cursor.fetchall()
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
    cursor.execute("""
        SELECT location, cuisine, COUNT(*) as count
        FROM restaurant
        GROUP BY location, cuisine
        ORDER BY location, cuisine
    """)
    combinations = cursor.fetchall()
    for row in combinations:
        print(f"   {row[0]} + {row[1]}: {row[2]}家")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"错误: {e}")
