from fastapi import APIRouter
import pymysql
from datetime import datetime

DB_HOST = "124.223.33.28"
DB_PORT = 3306
DB_USER = "cardData"
DB_PASSWORD = "zxN8TNNP4Ghf4Ksb"
DB_NAME = "carddata"

router = APIRouter()

def get_db_connection():
    """Establish and return MySQL database connection"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

@router.get("/rank/list", summary="Get user rank list by points")
def get_rank_list():
    """
    获取用户排行榜数据，按积分降序排列，显示用户名和积分
    
    Returns:
        list: 排行榜数据，包含用户名和积分
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查t_user表是否有points字段
        cursor.execute("SHOW COLUMNS FROM t_user LIKE 'points'")
        has_points = cursor.fetchone() is not None
        print(f"Points field exists: {has_points}")
        
        if has_points:
            # 查询用户积分排行榜，按积分降序排列，限制前100名
            cursor.execute(
                """
                SELECT username, points 
                FROM t_user 
                WHERE is_delete = 0 
                ORDER BY points DESC 
                LIMIT 100
                """
            )
            rank_list = cursor.fetchall()
            print(f"Rank list length: {len(rank_list)}")
        else:
            # 如果没有points字段，返回空列表
            rank_list = []
            # 尝试添加points字段到t_user表
            try:
                cursor.execute("ALTER TABLE t_user ADD COLUMN points INT DEFAULT 0")
                conn.commit()
                print("Added points column to t_user table")
            except Exception as e:
                print(f"Failed to add points column: {e}")
        
        conn.close()
        
        return rank_list
    except Exception as e:
        print(f"获取排行榜失败: {e}")
        return []

@router.get("/rank/user/{user_id}", summary="Get user rank by user ID")
def get_user_rank(user_id: int):
    """
    根据用户ID获取用户排名
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 包含用户排名和积分的字典
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 检查用户是否存在
        cursor.execute("SELECT points FROM t_user WHERE user_id = %s AND is_delete = 0", (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return {"rank": 0, "points": 0}
        
        user_points = user["points"]
        
        # 统计积分高于当前用户的人数
        cursor.execute("SELECT COUNT(*) as count FROM t_user WHERE points > %s AND is_delete = 0", (user_points,))
        higher_count = cursor.fetchone()["count"]
        
        # 计算排名（人数+1）
        rank = higher_count + 1
        conn.close()
        
        return {"rank": rank, "points": user_points}
    except Exception as e:
        print(f"获取用户排名失败: {e}")
        return {"rank": 0, "points": 0}
