from fastapi import APIRouter
import pymysql
from pydantic import BaseModel

DB_HOST = "124.223.33.28"
DB_PORT = 3306
DB_USER = "cardData"
DB_PASSWORD = "zxN8TNNP4Ghf4Ksb"
DB_NAME = "carddata"

router = APIRouter()


def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )


class AddPointsRequest(BaseModel):
    user_id: int
    points: int = 1


@router.post("/rank/add_points", summary="Add points to user")
def add_points(req: AddPointsRequest):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM t_user LIKE 'points'")
        if not cursor.fetchone():
            cursor.execute("ALTER TABLE t_user ADD COLUMN points INT DEFAULT 0")
            conn.commit()
        cursor.execute(
            "UPDATE t_user SET points = COALESCE(points, 0) + %s WHERE user_id = %s",
            (req.points, req.user_id)
        )
        conn.commit()
        cursor.execute("SELECT points FROM t_user WHERE user_id = %s", (req.user_id,))
        row = cursor.fetchone()
        conn.close()
        return {"status": "success", "points": row["points"] if row else None}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.get("/rank/user/{user_id}", summary="Get user rank by user ID")
def get_user_rank(user_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT points FROM t_user WHERE user_id = %s AND is_delete = 0", (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.close()
            return {"rank": 0, "points": 0}
        user_points = user["points"] or 0
        cursor.execute(
            "SELECT COUNT(*) as count FROM t_user WHERE points > %s AND is_delete = 0",
            (user_points,)
        )
        higher_count = cursor.fetchone()["count"]
        rank = higher_count + 1
        conn.close()
        return {"rank": rank, "points": user_points}
    except Exception as e:
        print(f"获取用户排名失败: {e}")
        return {"rank": 0, "points": 0}


@router.get("/rank/list", summary="Get user rank list by points")
def get_rank_list():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW COLUMNS FROM t_user LIKE 'points'")
        has_points = cursor.fetchone() is not None
        if has_points:
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
        else:
            rank_list = []
            try:
                cursor.execute("ALTER TABLE t_user ADD COLUMN points INT DEFAULT 0")
                conn.commit()
            except Exception as e:
                print(f"Failed to add points column: {e}")
        conn.close()
        return rank_list
    except Exception as e:
        print(f"获取排行榜失败: {e}")
        return []
