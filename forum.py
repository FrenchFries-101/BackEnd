# forum.py
# FastAPI 论坛模块
# 只负责论坛 API，不创建 FastAPI app 和数据库连接

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import List, Dict, Optional

# 数据库依赖从项目其他模块导入
from database import get_db

router = APIRouter(
    prefix="/forum",
    tags=["Forum"]
)


# ==============================
# 请求数据模型
# ==============================

class PostCreate(BaseModel):
    title: str
    content: str
    user_id: int


class ReplyCreate(BaseModel):
    content: str
    user_id: int


class LikeAction(BaseModel):
    user_id: int


# ==============================
# 获取帖子列表
# ==============================
"""
    返回值说明：
    - total: 总帖子数量
    - page: 当前页码
    - page_size: 每页条数
    - posts: 帖子列表数组
        - id: 帖子ID
        - title: 标题
        - author: 作者昵称
        - time: 发布日期（YYYY-MM-DD）
        - reply_count: 回复总数
        - likes: 点赞数
"""

@router.get("/posts")
def get_posts(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_post
        WHERE is_delete = 0
    """)).scalar() or 0

    rows = db.execute(text("""
        SELECT p.post_id, p.title, p.create_time, p.reply_count, p.like_count, u.username AS author
        FROM t_forum_post p
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE p.is_delete = 0
        ORDER BY p.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    posts = []

    for row in rows:
        posts.append({
            "id": row.post_id,
            "title": row.title,
            "author": row.author,
            "time": row.create_time.strftime("%Y-%m-%d"),
            "reply_count": row.reply_count,
            "likes": row.like_count
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "posts": posts
    }


# ==============================
# 搜索帖子
# ==============================
"""
    返回值说明：
    - total: 符合关键词的帖子总数
    - posts: 搜索结果列表（结构同帖子列表）
"""

@router.get("/posts/search")
def search_posts(keyword: str, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):

    keyword = f"%{keyword.strip()}%"

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_post
        WHERE is_delete = 0 AND title LIKE :keyword
    """), {"keyword": keyword}).scalar() or 0

    rows = db.execute(text("""
        SELECT p.post_id, p.title, p.create_time, p.reply_count, p.like_count, u.username AS author
        FROM t_forum_post p
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE p.is_delete = 0 AND p.title LIKE :keyword
        ORDER BY p.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "keyword": keyword,
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    posts = []

    for row in rows:
        posts.append({
            "id": row.post_id,
            "title": row.title,
            "author": row.author,
            "time": row.create_time.strftime("%Y-%m-%d"),
            "reply_count": row.reply_count,
            "likes": row.like_count
        })

    return {
        "total": total,
        "posts": posts
    }


# ==============================
# 帖子详情
# ==============================
"""
    返回值说明：
    - 找不到帖子：返回 null
    - 找到帖子：
        - id: 帖子ID
        - title: 标题
        - author: 作者昵称
        - time: 发布日期
        - content: 帖子内容
        - likes: 点赞数
"""

@router.get("/posts/{post_id}")
def get_post_detail(post_id: int, db: Session = Depends(get_db)):

    row = db.execute(text("""
        SELECT p.post_id, p.title, p.content, p.create_time, p.like_count, u.username AS author
        FROM t_forum_post p
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE p.post_id = :post_id AND p.is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not row:
        return None

    return {
        "id": row.post_id,
        "title": row.title,
        "author": row.author,
        "time": row.create_time.strftime("%Y-%m-%d"),
        "content": row.content,
        "likes": row.like_count
    }


# ==============================
# 获取回复
# ==============================
"""
    返回值说明：
    - 数组，每个元素代表一条回复
        - reply_id: 回复ID
        - author: 回复者昵称
        - content: 回复内容
        - likes: 回复点赞数
        - time: 回复时间（YYYY-MM-DD HH:MM）
    - 帖子不存在/无回复：返回空数组
"""

@router.get("/posts/{post_id}/replies")
def get_replies(post_id: int, db: Session = Depends(get_db)):

    exists = db.execute(text("""
        SELECT 1
        FROM t_forum_post
        WHERE post_id = :post_id AND is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not exists:
        return []

    rows = db.execute(text("""
        SELECT r.reply_id, r.content, r.create_time, r.like_count, u.username AS author
        FROM t_forum_reply r
        INNER JOIN t_user u ON r.user_id = u.user_id
        WHERE r.post_id = :post_id AND r.is_delete = 0
        ORDER BY r.create_time ASC
    """), {"post_id": post_id}).fetchall()

    result = []

    for row in rows:
        result.append({
            "reply_id": row.reply_id,
            "author": row.author,
            "content": row.content,
            "likes": row.like_count,
            "time": row.create_time.strftime("%Y-%m-%d %H:%M")
        })

    return result


# ==============================
# 获取用户点赞过的帖子
# ==============================
"""
    返回值说明：
    - user_id: 用户ID
    - total: 点赞过的帖子总数
    - posts: 帖子列表
        - post_id: 帖子ID
        - title: 标题
        - author: 作者昵称
        - time: 帖子发布时间（YYYY-MM-DD）
        - reply_count: 回复数
        - likes: 帖子总点赞数
        - liked_time: 用户点赞时间（YYYY-MM-DD HH:MM）
"""

@router.get("/users/{user_id}/liked-posts")
def get_user_liked_posts(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_post_like pl
        INNER JOIN t_forum_post p ON pl.post_id = p.post_id
        WHERE pl.user_id = :user_id
          AND p.is_delete = 0
    """), {
        "user_id": user_id
    }).scalar() or 0

    rows = db.execute(text("""
        SELECT
            p.post_id,
            p.title,
            p.create_time,
            p.reply_count,
            p.like_count,
            u.username AS author,
            pl.create_time AS liked_time
        FROM t_forum_post_like pl
        INNER JOIN t_forum_post p ON pl.post_id = p.post_id
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE pl.user_id = :user_id
          AND p.is_delete = 0
        ORDER BY pl.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "user_id": user_id,
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    posts = []

    for row in rows:
        posts.append({
            "post_id": row.post_id,
            "title": row.title,
            "author": row.author,
            "time": row.create_time.strftime("%Y-%m-%d"),
            "reply_count": row.reply_count,
            "likes": row.like_count,
            "liked_time": row.liked_time.strftime("%Y-%m-%d %H:%M") if row.liked_time else None
        })

    return {
        "user_id": user_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "posts": posts
    }


# ==============================
# 获取用户点赞过的回复
# ==============================
"""
    返回值说明：
    - user_id: 用户ID
    - total: 点赞过的回复总数
    - replies: 回复列表
        - reply_id: 回复ID
        - post_id: 所属帖子ID
        - author: 回复作者昵称
        - content: 回复内容
        - likes: 回复总点赞数
        - time: 回复发布时间（YYYY-MM-DD HH:MM）
        - liked_time: 用户点赞时间（YYYY-MM-DD HH:MM）
"""

@router.get("/users/{user_id}/liked-replies")
def get_user_liked_replies(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_reply_like rl
        INNER JOIN t_forum_reply r ON rl.reply_id = r.reply_id
        WHERE rl.user_id = :user_id
          AND r.is_delete = 0
    """), {
        "user_id": user_id
    }).scalar() or 0

    rows = db.execute(text("""
        SELECT
            r.reply_id,
            r.post_id,
            r.content,
            r.create_time,
            r.like_count,
            u.username AS author,
            rl.create_time AS liked_time
        FROM t_forum_reply_like rl
        INNER JOIN t_forum_reply r ON rl.reply_id = r.reply_id
        INNER JOIN t_user u ON r.user_id = u.user_id
        WHERE rl.user_id = :user_id
          AND r.is_delete = 0
        ORDER BY rl.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "user_id": user_id,
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    replies = []

    for row in rows:
        replies.append({
            "reply_id": row.reply_id,
            "post_id": row.post_id,
            "author": row.author,
            "content": row.content,
            "likes": row.like_count,
            "time": row.create_time.strftime("%Y-%m-%d %H:%M"),
            "liked_time": row.liked_time.strftime("%Y-%m-%d %H:%M") if row.liked_time else None
        })

    return {
        "user_id": user_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "replies": replies
    }


# ==============================
# 创建帖子
# ==============================
"""
    返回值说明：
    - 成功：{"status": "ok", "post_id": 新帖子ID}
    - 失败：{"status": "error", "message": 错误原因}
"""

@router.post("/posts")
def create_post(data: PostCreate, db: Session = Depends(get_db)):

    if not data.title.strip():
        return {"status": "error", "message": "The title cannot be empty"}

    if not data.content.strip():
        return {"status": "error", "message": "The content cannot be empty"}

    now = datetime.now()

    try:

        result = db.execute(text("""
            INSERT INTO t_forum_post
            (user_id, title, content, reply_count, like_count, create_time, update_time, is_delete)
            VALUES (:user_id, :title, :content, 0, 0, :now, :now, 0)
        """), {
            "user_id": data.user_id,
            "title": data.title.strip(),
            "content": data.content.strip(),
            "now": now
        })

        db.commit()

        return {
            "status": "ok",
            "post_id": result.lastrowid
        }

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }


# ==============================
# 回复帖子
# ==============================
"""
    返回值说明：
    - 成功：{"status": "ok"}
    - 失败：{"status": "error", "message": 错误原因}
"""

@router.post("/posts/{post_id}/reply")
def reply_post(post_id: int, data: ReplyCreate, db: Session = Depends(get_db)):

    post_exists = db.execute(text("""
        SELECT 1 FROM t_forum_post
        WHERE post_id = :post_id AND is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not post_exists:
        return {"status": "error", "message": "Post not found"}

    if not data.content.strip():
        return {"status": "error", "message": "Reply cannot be empty"}

    now = datetime.now()

    try:

        db.execute(text("""
            INSERT INTO t_forum_reply
            (post_id, user_id, content, like_count, create_time, is_delete)
            VALUES (:post_id, :user_id, :content, 0, :now, 0)
        """), {
            "post_id": post_id,
            "user_id": data.user_id,
            "content": data.content.strip(),
            "now": now
        })

        db.execute(text("""
            UPDATE t_forum_post
            SET reply_count = reply_count + 1,
                update_time = :now
            WHERE post_id = :post_id
        """), {
            "post_id": post_id,
            "now": now
        })

        db.commit()

        return {"status": "ok"}

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }


# ==============================
# 点赞帖子
# ==============================
"""
    返回值说明：
    - 成功：
        status: ok
        action: liked（点赞）/ unliked（取消点赞）
        likes: 当前最新点赞总数
    - 失败：
        status: error
        message: 错误原因
"""

@router.post("/posts/{post_id}/like")
def like_post(post_id: int, data: LikeAction, db: Session = Depends(get_db)):

    user_id = data.user_id
    now = datetime.now()

    post_exists = db.execute(text("""
        SELECT 1 FROM t_forum_post
        WHERE post_id = :post_id AND is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not post_exists:
        return {"status": "error", "message": "Post not found"}

    like_record = db.execute(text("""
        SELECT like_id FROM t_forum_post_like
        WHERE post_id = :post_id AND user_id = :user_id
        LIMIT 1
    """), {
        "post_id": post_id,
        "user_id": user_id
    }).fetchone()

    try:

        if like_record:

            db.execute(text("""
                DELETE FROM t_forum_post_like
                WHERE post_id = :post_id AND user_id = :user_id
            """), {
                "post_id": post_id,
                "user_id": user_id
            })

            db.execute(text("""
                UPDATE t_forum_post
                SET like_count = GREATEST(like_count - 1, 0),
                    update_time = :now
                WHERE post_id = :post_id
            """), {
                "post_id": post_id,
                "now": now
            })

            action = "unliked"

        else:

            db.execute(text("""
                INSERT INTO t_forum_post_like (post_id, user_id, create_time)
                VALUES (:post_id, :user_id, :now)
            """), {
                "post_id": post_id,
                "user_id": user_id,
                "now": now
            })

            db.execute(text("""
                UPDATE t_forum_post
                SET like_count = like_count + 1,
                    update_time = :now
                WHERE post_id = :post_id
            """), {
                "post_id": post_id,
                "now": now
            })

            action = "liked"

        db.commit()

        current_likes = db.execute(text("""
            SELECT like_count FROM t_forum_post
            WHERE post_id = :post_id
        """), {"post_id": post_id}).scalar() or 0

        return {
            "status": "ok",
            "action": action,
            "likes": current_likes
        }

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }


# ==============================
# 点赞回复
# ==============================
"""
    返回值说明：
    - 成功：
        status: ok
        action: liked / unliked
        likes: 当前回复最新点赞数
    - 失败：
        status: error
        message: 错误原因
"""

@router.post("/replies/{reply_id}/like")
def like_reply(reply_id: int, data: LikeAction, db: Session = Depends(get_db)):

    user_id = data.user_id
    now = datetime.now()

    reply_exists = db.execute(text("""
        SELECT 1 FROM t_forum_reply
        WHERE reply_id = :reply_id AND is_delete = 0
        LIMIT 1
    """), {"reply_id": reply_id}).fetchone()

    if not reply_exists:
        return {"status": "error", "message": "Reply not found"}

    like_record = db.execute(text("""
        SELECT like_id FROM t_forum_reply_like
        WHERE reply_id = :reply_id AND user_id = :user_id
        LIMIT 1
    """), {
        "reply_id": reply_id,
        "user_id": user_id
    }).fetchone()

    try:

        if like_record:

            db.execute(text("""
                DELETE FROM t_forum_reply_like
                WHERE reply_id = :reply_id AND user_id = :user_id
            """), {
                "reply_id": reply_id,
                "user_id": user_id
            })

            db.execute(text("""
                UPDATE t_forum_reply
                SET like_count = GREATEST(like_count - 1, 0)
                WHERE reply_id = :reply_id
            """), {"reply_id": reply_id})

            action = "unliked"

        else:

            db.execute(text("""
                INSERT INTO t_forum_reply_like (reply_id, user_id, create_time)
                VALUES (:reply_id, :user_id, :now)
            """), {
                "reply_id": reply_id,
                "user_id": user_id,
                "now": now
            })

            db.execute(text("""
                UPDATE t_forum_reply
                SET like_count = like_count + 1
                WHERE reply_id = :reply_id
            """), {"reply_id": reply_id})

            action = "liked"

        db.commit()

        current_likes = db.execute(text("""
            SELECT like_count FROM t_forum_reply
            WHERE reply_id = :reply_id
        """), {"reply_id": reply_id}).scalar() or 0

        return {
            "status": "ok",
            "action": action,
            "likes": current_likes
        }

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }# forum.py
# FastAPI 论坛模块
# 只负责论坛 API，不创建 FastAPI app 和数据库连接

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
from typing import List, Dict, Optional

# 数据库依赖从项目其他模块导入
from database import get_db

router = APIRouter(
    prefix="/forum",
    tags=["Forum"]
)


# ==============================
# 请求数据模型
# ==============================

class PostCreate(BaseModel):
    title: str
    content: str
    user_id: int


class ReplyCreate(BaseModel):
    content: str
    user_id: int


class LikeAction(BaseModel):
    user_id: int


# ==============================
# 获取帖子列表
# ==============================
"""
    返回值说明：
    - total: 总帖子数量
    - page: 当前页码
    - page_size: 每页条数
    - posts: 帖子列表数组
        - id: 帖子ID
        - title: 标题
        - author: 作者昵称
        - time: 发布日期（YYYY-MM-DD）
        - reply_count: 回复总数
        - likes: 点赞数
"""

@router.get("/posts")
def get_posts(page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_post
        WHERE is_delete = 0
    """)).scalar() or 0

    rows = db.execute(text("""
        SELECT p.post_id, p.title, p.create_time, p.reply_count, p.like_count, u.username AS author
        FROM t_forum_post p
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE p.is_delete = 0
        ORDER BY p.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    posts = []

    for row in rows:
        posts.append({
            "id": row.post_id,
            "title": row.title,
            "author": row.author,
            "time": row.create_time.strftime("%Y-%m-%d"),
            "reply_count": row.reply_count,
            "likes": row.like_count
        })

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "posts": posts
    }


# ==============================
# 搜索帖子
# ==============================
"""
    返回值说明：
    - total: 符合关键词的帖子总数
    - posts: 搜索结果列表（结构同帖子列表）
"""

@router.get("/posts/search")
def search_posts(keyword: str, page: int = 1, page_size: int = 20, db: Session = Depends(get_db)):

    keyword = f"%{keyword.strip()}%"

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_post
        WHERE is_delete = 0 AND title LIKE :keyword
    """), {"keyword": keyword}).scalar() or 0

    rows = db.execute(text("""
        SELECT p.post_id, p.title, p.create_time, p.reply_count, p.like_count, u.username AS author
        FROM t_forum_post p
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE p.is_delete = 0 AND p.title LIKE :keyword
        ORDER BY p.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "keyword": keyword,
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    posts = []

    for row in rows:
        posts.append({
            "id": row.post_id,
            "title": row.title,
            "author": row.author,
            "time": row.create_time.strftime("%Y-%m-%d"),
            "reply_count": row.reply_count,
            "likes": row.like_count
        })

    return {
        "total": total,
        "posts": posts
    }


# ==============================
# 帖子详情
# ==============================
"""
    返回值说明：
    - 找不到帖子：返回 null
    - 找到帖子：
        - id: 帖子ID
        - title: 标题
        - author: 作者昵称
        - time: 发布日期
        - content: 帖子内容
        - likes: 点赞数
"""

@router.get("/posts/{post_id}")
def get_post_detail(post_id: int, db: Session = Depends(get_db)):

    row = db.execute(text("""
        SELECT p.post_id, p.title, p.content, p.create_time, p.like_count, u.username AS author
        FROM t_forum_post p
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE p.post_id = :post_id AND p.is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not row:
        return None

    return {
        "id": row.post_id,
        "title": row.title,
        "author": row.author,
        "time": row.create_time.strftime("%Y-%m-%d"),
        "content": row.content,
        "likes": row.like_count
    }


# ==============================
# 获取回复
# ==============================
"""
    返回值说明：
    - 数组，每个元素代表一条回复
        - reply_id: 回复ID
        - author: 回复者昵称
        - content: 回复内容
        - likes: 回复点赞数
        - time: 回复时间（YYYY-MM-DD HH:MM）
    - 帖子不存在/无回复：返回空数组
"""

@router.get("/posts/{post_id}/replies")
def get_replies(post_id: int, db: Session = Depends(get_db)):

    exists = db.execute(text("""
        SELECT 1
        FROM t_forum_post
        WHERE post_id = :post_id AND is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not exists:
        return []

    rows = db.execute(text("""
        SELECT r.reply_id, r.content, r.create_time, r.like_count, u.username AS author
        FROM t_forum_reply r
        INNER JOIN t_user u ON r.user_id = u.user_id
        WHERE r.post_id = :post_id AND r.is_delete = 0
        ORDER BY r.create_time ASC
    """), {"post_id": post_id}).fetchall()

    result = []

    for row in rows:
        result.append({
            "reply_id": row.reply_id,
            "author": row.author,
            "content": row.content,
            "likes": row.like_count,
            "time": row.create_time.strftime("%Y-%m-%d %H:%M")
        })

    return result

# ==============================
#用户是否给某个reply点过赞
# ==============================

@router.get("/replies/{reply_id}/is-liked")
def is_reply_liked(reply_id: int, user_id: int, db: Session = Depends(get_db)):

    result = db.execute(text("""
        SELECT 1 FROM t_forum_reply_like
        WHERE reply_id = :reply_id AND user_id = :user_id
        LIMIT 1
    """), {
        "reply_id": reply_id,
        "user_id": user_id
    }).fetchone()

    return {
        "liked": True if result else False
    }

# ==============================
#用户点过没有post
# ==============================


@router.get("/posts/{post_id}/is-liked")
def is_post_liked(post_id: int, user_id: int, db: Session = Depends(get_db)):

    result = db.execute(text("""
        SELECT 1 FROM t_forum_post_like
        WHERE post_id = :post_id AND user_id = :user_id
        LIMIT 1
    """), {
        "post_id": post_id,
        "user_id": user_id
    }).fetchone()

    return {
        "liked": True if result else False
    }

# ==============================
# 获取用户点赞过的帖子
# ==============================
"""
    返回值说明：
    - user_id: 用户ID
    - total: 点赞过的帖子总数
    - posts: 帖子列表
        - post_id: 帖子ID
        - title: 标题
        - author: 作者昵称
        - time: 帖子发布时间（YYYY-MM-DD）
        - reply_count: 回复数
        - likes: 帖子总点赞数
        - liked_time: 用户点赞时间（YYYY-MM-DD HH:MM）
"""

@router.get("/users/{user_id}/liked-posts")
def get_user_liked_posts(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_post_like pl
        INNER JOIN t_forum_post p ON pl.post_id = p.post_id
        WHERE pl.user_id = :user_id
          AND p.is_delete = 0
    """), {
        "user_id": user_id
    }).scalar() or 0

    rows = db.execute(text("""
        SELECT
            p.post_id,
            p.title,
            p.create_time,
            p.reply_count,
            p.like_count,
            u.username AS author,
            pl.create_time AS liked_time
        FROM t_forum_post_like pl
        INNER JOIN t_forum_post p ON pl.post_id = p.post_id
        INNER JOIN t_user u ON p.user_id = u.user_id
        WHERE pl.user_id = :user_id
          AND p.is_delete = 0
        ORDER BY pl.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "user_id": user_id,
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    posts = []

    for row in rows:
        posts.append({
            "post_id": row.post_id,
            "title": row.title,
            "author": row.author,
            "time": row.create_time.strftime("%Y-%m-%d"),
            "reply_count": row.reply_count,
            "likes": row.like_count,
            "liked_time": row.liked_time.strftime("%Y-%m-%d %H:%M") if row.liked_time else None
        })

    return {
        "user_id": user_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "posts": posts
    }


# ==============================
# 获取用户点赞过的回复
# ==============================
"""
    返回值说明：
    - user_id: 用户ID
    - total: 点赞过的回复总数
    - replies: 回复列表
        - reply_id: 回复ID
        - post_id: 所属帖子ID
        - author: 回复作者昵称
        - content: 回复内容
        - likes: 回复总点赞数
        - time: 回复发布时间（YYYY-MM-DD HH:MM）
        - liked_time: 用户点赞时间（YYYY-MM-DD HH:MM）
"""

@router.get("/users/{user_id}/liked-replies")
def get_user_liked_replies(
    user_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db)
):

    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 20

    offset = (page - 1) * page_size

    total = db.execute(text("""
        SELECT COUNT(*)
        FROM t_forum_reply_like rl
        INNER JOIN t_forum_reply r ON rl.reply_id = r.reply_id
        WHERE rl.user_id = :user_id
          AND r.is_delete = 0
    """), {
        "user_id": user_id
    }).scalar() or 0

    rows = db.execute(text("""
        SELECT
            r.reply_id,
            r.post_id,
            r.content,
            r.create_time,
            r.like_count,
            u.username AS author,
            rl.create_time AS liked_time
        FROM t_forum_reply_like rl
        INNER JOIN t_forum_reply r ON rl.reply_id = r.reply_id
        INNER JOIN t_user u ON r.user_id = u.user_id
        WHERE rl.user_id = :user_id
          AND r.is_delete = 0
        ORDER BY rl.create_time DESC
        LIMIT :offset, :page_size
    """), {
        "user_id": user_id,
        "offset": offset,
        "page_size": page_size
    }).fetchall()

    replies = []

    for row in rows:
        replies.append({
            "reply_id": row.reply_id,
            "post_id": row.post_id,
            "author": row.author,
            "content": row.content,
            "likes": row.like_count,
            "time": row.create_time.strftime("%Y-%m-%d %H:%M"),
            "liked_time": row.liked_time.strftime("%Y-%m-%d %H:%M") if row.liked_time else None
        })

    return {
        "user_id": user_id,
        "total": total,
        "page": page,
        "page_size": page_size,
        "replies": replies
    }


# ==============================
# 创建帖子
# ==============================
"""
    返回值说明：
    - 成功：{"status": "ok", "post_id": 新帖子ID}
    - 失败：{"status": "error", "message": 错误原因}
"""

@router.post("/posts")
def create_post(data: PostCreate, db: Session = Depends(get_db)):

    if not data.title.strip():
        return {"status": "error", "message": "The title cannot be empty"}

    if not data.content.strip():
        return {"status": "error", "message": "The content cannot be empty"}

    now = datetime.now()

    try:

        result = db.execute(text("""
            INSERT INTO t_forum_post
            (user_id, title, content, reply_count, like_count, create_time, update_time, is_delete)
            VALUES (:user_id, :title, :content, 0, 0, :now, :now, 0)
        """), {
            "user_id": data.user_id,
            "title": data.title.strip(),
            "content": data.content.strip(),
            "now": now
        })

        db.commit()

        return {
            "status": "ok",
            "post_id": result.lastrowid
        }

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }


# ==============================
# 回复帖子
# ==============================
"""
    返回值说明：
    - 成功：{"status": "ok"}
    - 失败：{"status": "error", "message": 错误原因}
"""

@router.post("/posts/{post_id}/reply")
def reply_post(post_id: int, data: ReplyCreate, db: Session = Depends(get_db)):

    post_exists = db.execute(text("""
        SELECT 1 FROM t_forum_post
        WHERE post_id = :post_id AND is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not post_exists:
        return {"status": "error", "message": "Post not found"}

    if not data.content.strip():
        return {"status": "error", "message": "Reply cannot be empty"}

    now = datetime.now()

    try:

        db.execute(text("""
            INSERT INTO t_forum_reply
            (post_id, user_id, content, like_count, create_time, is_delete)
            VALUES (:post_id, :user_id, :content, 0, :now, 0)
        """), {
            "post_id": post_id,
            "user_id": data.user_id,
            "content": data.content.strip(),
            "now": now
        })

        db.execute(text("""
            UPDATE t_forum_post
            SET reply_count = reply_count + 1,
                update_time = :now
            WHERE post_id = :post_id
        """), {
            "post_id": post_id,
            "now": now
        })

        db.commit()

        return {"status": "ok"}

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }


# ==============================
# 点赞帖子
# ==============================
"""
    返回值说明：
    - 成功：
        status: ok
        action: liked（点赞）/ unliked（取消点赞）
        likes: 当前最新点赞总数
    - 失败：
        status: error
        message: 错误原因
"""

@router.post("/posts/{post_id}/like")
def like_post(post_id: int, data: LikeAction, db: Session = Depends(get_db)):

    user_id = data.user_id
    now = datetime.now()

    post_exists = db.execute(text("""
        SELECT 1 FROM t_forum_post
        WHERE post_id = :post_id AND is_delete = 0
        LIMIT 1
    """), {"post_id": post_id}).fetchone()

    if not post_exists:
        return {"status": "error", "message": "Post not found"}

    like_record = db.execute(text("""
        SELECT like_id FROM t_forum_post_like
        WHERE post_id = :post_id AND user_id = :user_id
        LIMIT 1
    """), {
        "post_id": post_id,
        "user_id": user_id
    }).fetchone()

    try:

        if like_record:

            db.execute(text("""
                DELETE FROM t_forum_post_like
                WHERE post_id = :post_id AND user_id = :user_id
            """), {
                "post_id": post_id,
                "user_id": user_id
            })

            db.execute(text("""
                UPDATE t_forum_post
                SET like_count = GREATEST(like_count - 1, 0),
                    update_time = :now
                WHERE post_id = :post_id
            """), {
                "post_id": post_id,
                "now": now
            })

            action = "unliked"

        else:

            db.execute(text("""
                INSERT INTO t_forum_post_like (post_id, user_id, create_time)
                VALUES (:post_id, :user_id, :now)
            """), {
                "post_id": post_id,
                "user_id": user_id,
                "now": now
            })

            db.execute(text("""
                UPDATE t_forum_post
                SET like_count = like_count + 1,
                    update_time = :now
                WHERE post_id = :post_id
            """), {
                "post_id": post_id,
                "now": now
            })

            action = "liked"

        db.commit()

        current_likes = db.execute(text("""
            SELECT like_count FROM t_forum_post
            WHERE post_id = :post_id
        """), {"post_id": post_id}).scalar() or 0

        return {
            "status": "ok",
            "action": action,
            "likes": current_likes
        }

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }


# ==============================
# 点赞回复
# ==============================
"""
    返回值说明：
    - 成功：
        status: ok
        action: liked / unliked
        likes: 当前回复最新点赞数
    - 失败：
        status: error
        message: 错误原因
"""

@router.post("/replies/{reply_id}/like")
def like_reply(reply_id: int, data: LikeAction, db: Session = Depends(get_db)):

    user_id = data.user_id
    now = datetime.now()

    reply_exists = db.execute(text("""
        SELECT 1 FROM t_forum_reply
        WHERE reply_id = :reply_id AND is_delete = 0
        LIMIT 1
    """), {"reply_id": reply_id}).fetchone()

    if not reply_exists:
        return {"status": "error", "message": "Reply not found"}

    like_record = db.execute(text("""
        SELECT like_id FROM t_forum_reply_like
        WHERE reply_id = :reply_id AND user_id = :user_id
        LIMIT 1
    """), {
        "reply_id": reply_id,
        "user_id": user_id
    }).fetchone()

    try:

        if like_record:

            db.execute(text("""
                DELETE FROM t_forum_reply_like
                WHERE reply_id = :reply_id AND user_id = :user_id
            """), {
                "reply_id": reply_id,
                "user_id": user_id
            })

            db.execute(text("""
                UPDATE t_forum_reply
                SET like_count = GREATEST(like_count - 1, 0)
                WHERE reply_id = :reply_id
            """), {"reply_id": reply_id})

            action = "unliked"

        else:

            db.execute(text("""
                INSERT INTO t_forum_reply_like (reply_id, user_id, create_time)
                VALUES (:reply_id, :user_id, :now)
            """), {
                "reply_id": reply_id,
                "user_id": user_id,
                "now": now
            })

            db.execute(text("""
                UPDATE t_forum_reply
                SET like_count = like_count + 1
                WHERE reply_id = :reply_id
            """), {"reply_id": reply_id})

            action = "liked"

        db.commit()

        current_likes = db.execute(text("""
            SELECT like_count FROM t_forum_reply
            WHERE reply_id = :reply_id
        """), {"reply_id": reply_id}).scalar() or 0

        return {
            "status": "ok",
            "action": action,
            "likes": current_likes
        }

    except Exception as e:

        db.rollback()

        return {
            "status": "error",
            "message": str(e)
        }