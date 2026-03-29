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


# --------------------------
# 创建 FastAPI 应用实例
# --------------------------
app = FastAPI(
    title="AcadamicEnglish",
    description="Backend Interfaces",
    version="1.0.0"
)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --------------------------
# 注册所有模块的路由
# --------------------------
app.include_router(listening_router)  # 监听接口，前缀 /listening
app.include_router(word_router)       # 单词接口，前缀 /word
app.include_router(forum_router)      # 论坛接口，前缀 /forum
app.include_router(login_router)      # 登录接口（假设前缀 /login）
app.include_router(speaking_router)
app.include_router(ted_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "API is serving"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",   # 文件名:变量名
        host="127.0.0.1",
        port=8000,
        reload=True   # 开发模式自动重载
    )


from database import get_db
