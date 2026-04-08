from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from fastapi.staticfiles import StaticFiles
from pathlib import Path

# 导入各模块的路由
from listening import router as listening_router
from word import router as word_router
from forum import router as forum_router
from Login import router as login_router
from speaking import router as speaking_router
from ted import router as ted_router
from rank import router as rank_router
from group import router as group_router
from word_game import router as word_game_router
from pet import router as pet_router, init_pet_db   # ✅ 同一行导入更清晰
from recommendation.restaurant import router as restaurant_router, init_restaurant_db  # ✅ 美食推荐模块
from recommendation.changsha import router as changsha_router, init_city_db  # ✅ 城市信息模块

# --------------------------
# 创建 FastAPI 应用实例
# --------------------------
app = FastAPI(
    title="AcadamicEnglish",
    description="Backend Interfaces",
    version="1.0.0"
)

# --------------------------
# 静态文件挂载
# --------------------------
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
HEAD_DIR = BASE_DIR / "head"
HEAD_DIR.mkdir(parents=True, exist_ok=True)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --------------------------
# 注册所有模块的路由
# 注册所有模块的路由
app.include_router(listening_router)  # 监听接口，前缀 /listening
app.include_router(word_router)       # 单词接口，前缀 /word
app.include_router(forum_router)      # 论坛接口，前缀 /forum
app.include_router(login_router)      # 登录接口（假设前缀 /login）
app.include_router(speaking_router)
app.include_router(ted_router)
app.include_router(rank_router)       # 排行榜接口，前缀 /rank
app.include_router(group_router)      # 小组接口，前缀 /groups
app.include_router(word_game_router)
app.include_router(restaurant_router)  # ✅ 美食推荐模块接口，前缀 /api/restaurant
app.include_router(changsha_router)     # ✅ 城市信息模块接口，前缀 /api/city

# CORS 跨域中间件（放在路由注册之前）
# --------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------------------------
# 注册所有模块的路由
# --------------------------
app.include_router(listening_router)
app.include_router(word_router)
app.include_router(forum_router)
app.include_router(login_router)
app.include_router(speaking_router)
app.include_router(ted_router)
app.include_router(rank_router)
app.include_router(group_router)
app.include_router(pet_router)      # ✅ 宠物模块路由

# --------------------------
# 启动事件：初始化数据库
# --------------------------
@app.on_event("startup")
def on_startup():
    init_pet_db()               # ✅ 修复：启动时初始化宠物数据库表 + 种子数据
    init_restaurant_db()        # ✅ 初始化美食推荐数据库表
    init_city_db()              # ✅ 初始化城市信息数据库表
    
    # 初始化美食推荐种子数据
    from database import SessionLocal
    from recommendation.seed import seed_restaurant_data
    from recommendation.changsha_seed import seed_city_data
    from sqlalchemy.orm import sessionmaker
    from database import engine
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = Session()
    try:
        seed_restaurant_data(db)
        seed_city_data(db)
    finally:
        db.close()

# --------------------------
# 根路由健康检查
# --------------------------
@app.get("/")
def root():
    return {"message": "API is serving"}

# --------------------------
# 本地开发入口
# --------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True
    )
