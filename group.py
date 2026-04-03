from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from pydantic import BaseModel
from datetime import datetime, date
from pathlib import Path
import base64
import hashlib
import uuid
from database import get_db


router = APIRouter(prefix="/groups", tags=["groups"])

BASE_DIR = Path(__file__).resolve().parent
GROUP_HEAD_DIR = BASE_DIR / "head"
GROUP_HEAD_DIR.mkdir(parents=True, exist_ok=True)
GROUP_HEAD_BASE_PATH = "head"


# 数据模型
from models import Base
from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey


class Group(Base):
    __tablename__ = "t_group"

    group_id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_name = Column(String(50), nullable=False)
    creator_id = Column(BigInteger, nullable=False)
    max_members = Column(Integer, nullable=False)
    group_icon = Column(String(255), nullable=True)
    password = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class GroupMember(Base):
    __tablename__ = "t_group_member"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    role = Column(String(20), nullable=False)
    join_time = Column(DateTime, default=datetime.utcnow)


class GroupMessage(Base):
    __tablename__ = "t_group_message"

    message_id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False)
    sender_id = Column(BigInteger, nullable=False)
    content = Column(String(1000), nullable=False)
    message_type = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    __tablename__ = "t_activity_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    group_id = Column(BigInteger, nullable=False)
    activity_type = Column(String(20), nullable=False)
    amount = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GroupWeeklyProgress(Base):
    __tablename__ = "t_group_weekly_progress"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False)
    week = Column(Integer, nullable=False)
    activity_type = Column(String(20), nullable=False)
    total_amount = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class UserWeeklyContribution(Base):
    __tablename__ = "t_user_weekly_contribution"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    week = Column(Integer, nullable=False)
    activity_type = Column(String(20), nullable=False)
    amount = Column(Integer, default=0)


class RewardLog(Base):
    __tablename__ = "t_reward_log"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    group_id = Column(BigInteger, nullable=False)
    activity_type = Column(String(20), nullable=False)
    goal_type = Column(String(20), nullable=False)
    coins = Column(Integer, nullable=False)
    status = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "t_user"

    user_id = Column(BigInteger, primary_key=True, autoincrement=True)
    email = Column(String(50), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    username = Column(String(30), nullable=True)
    points = Column(Integer, default=0)
    create_time = Column(DateTime, default=datetime.utcnow)
    update_time = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_delete = Column(Integer, default=0)


# Pydantic模型
class GroupCreate(BaseModel):
    user_id: int
    group_name: str
    max_members: int
    group_icon: str = None
    password: str = None


class GroupJoin(BaseModel):
    user_id: int
    group_id: int
    password: str = None


class MessageSend(BaseModel):
    sender_id: int
    content: str
    message_type: str


class ActivitySubmit(BaseModel):
    user_id: int
    activity_type: str
    amount: int


# 辅助函数
def get_week_number():
    """获取当前是当年的第几周"""
    return date.today().isocalendar()[1]


def hash_password(password):
    """密码加密"""
    if not password:
        return None
    return hashlib.sha256(password.encode()).hexdigest()


def check_password(hashed_password, password):
    """密码验证"""
    if not hashed_password:
        return True
    return hashlib.sha256(password.encode()).hexdigest() == hashed_password


def get_image_suffix(filename, content_type):
    if filename:
        suffix = Path(filename).suffix.lower()
        if suffix in [".jpg", ".jpeg", ".png", ".gif", ".webp"]:
            return suffix

    content_type_map = {
        "image/jpeg": ".jpg",
        "image/jpg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp"
    }
    return content_type_map.get(content_type, ".jpg")


def decode_base64_image(image_base64):
    content = (image_base64 or "").strip()
    if not content:
        raise ValueError("base64图片内容不能为空")

    content_type = None
    if content.startswith("data:image/") and "," in content:
        header, content = content.split(",", 1)
        if ";" in header:
            content_type = header.split(";")[0].replace("data:", "")

    try:
        image_bytes = base64.b64decode(content, validate=True)
    except Exception as exc:
        raise ValueError("base64图片格式不正确") from exc

    if not image_bytes:
        raise ValueError("图片内容不能为空")

    return image_bytes, get_image_suffix(None, content_type)


# API接口
@router.get("/")
async def get_groups(
    search: str = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取小组列表"""
    query = db.query(Group)
    
    if search:
        query = query.filter(Group.group_name.contains(search))
    
    total_count = query.count()
    
    groups = query.offset((page - 1) * page_size).limit(page_size).all()
    
    result = []
    for group in groups:
        # 计算当前成员数
        current_members = db.query(GroupMember).filter(GroupMember.group_id == group.group_id).count()
        
        result.append({
            "group_id": group.group_id,
            "group_name": group.group_name,
            "current_members": current_members,
            "max_members": group.max_members,
            "group_icon": group.group_icon,
            "creator_id": group.creator_id,
            "password": getattr(group, "password", None) is None
        })
    
    return {
        "groups": result,
        "total_count": total_count
    }


@router.post("/create")
async def create_group(
    group_data: GroupCreate,
    db: Session = Depends(get_db)
):
    """创建新小组"""
    # 验证最大成员数
    if group_data.max_members < 2 or group_data.max_members > 4:
        raise HTTPException(status_code=400, detail="最大成员数必须在2-4之间")
    
    # 创建小组
    new_group = Group(
        group_name=group_data.group_name,
        creator_id=group_data.user_id if hasattr(group_data, 'user_id') else 0,  # 需要从认证中获取
        max_members=group_data.max_members,
        group_icon=group_data.group_icon,
        password=hash_password(group_data.password)
    )
    
    db.add(new_group)
    db.commit()
    db.refresh(new_group)
    
    # 创建者自动加入小组
    new_member = GroupMember(
        group_id=new_group.group_id,
        user_id=new_group.creator_id,
        role="leader"
    )
    db.add(new_member)
    db.commit()
    
    return {
        "success": True,
        "group_id": new_group.group_id,
        "message": "小组创建成功"
    }


@router.post("/{group_id}/icon")
async def upload_group_icon(
    group_id: int,
    request: Request,
    image: UploadFile | None = File(None),
    image_base64: str | None = Form(None),
    db: Session = Depends(get_db)
):
    """上传小组头像并回写URL"""
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")

    image_bytes = None
    suffix = ".jpg"

    if image is not None:
        image_bytes = await image.read()
        if not image_bytes:
            raise HTTPException(status_code=400, detail="上传图片不能为空")
        suffix = get_image_suffix(image.filename, image.content_type)
    elif image_base64:
        try:
            image_bytes, suffix = decode_base64_image(image_base64)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        raise HTTPException(status_code=400, detail="请上传图片文件或传入base64图片")

    filename = f"group_{group_id}_{uuid.uuid4().hex}{suffix}"
    file_path = GROUP_HEAD_DIR / filename
    file_path.write_bytes(image_bytes)

    base_url = str(request.base_url).rstrip("/")
    image_url = f"{base_url}/{GROUP_HEAD_BASE_PATH}/{filename}"
    setattr(group, "group_icon", image_url)
    db.commit()

    return {
        "success": True,
        "group_id": group_id,
        "group_icon": image_url,
        "message": "头像上传成功"
    }


@router.post("/join")
async def join_group(
    join_data: GroupJoin,
    db: Session = Depends(get_db)
):
    """加入小组"""
    # 查找小组
    group = db.query(Group).filter(Group.group_id == join_data.group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")
    
    # 验证密码
    if group.password and not check_password(group.password, join_data.password):
        raise HTTPException(status_code=401, detail="密码错误")
    
    # 检查是否已经加入
    existing_member = db.query(GroupMember).filter(
        and_(GroupMember.group_id == join_data.group_id,
             GroupMember.user_id == join_data.user_id if hasattr(join_data, 'user_id') else 0)
    ).first()
    if existing_member:
        raise HTTPException(status_code=400, detail="已经加入该小组")
    
    # 检查人数是否已满
    current_members = db.query(GroupMember).filter(GroupMember.group_id == join_data.group_id).count()
    if current_members >= group.max_members:
        raise HTTPException(status_code=400, detail="小组人数已满")
    
    # 加入小组
    new_member = GroupMember(
        group_id=join_data.group_id,
        user_id=join_data.user_id if hasattr(join_data, 'user_id') else 0,  # 需要从认证中获取
        role="member"
    )
    db.add(new_member)
    db.commit()
    
    return {
        "success": True,
        "message": "加入小组成功",
        "group_id": join_data.group_id
    }


@router.get("/user/{user_id}/groups")
async def get_user_groups(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取某个用户所在的所有小组及身份"""
    rows = db.query(
        GroupMember.group_id,
        GroupMember.role,
        Group.group_name,
        Group.group_icon
    ).join(
        Group,
        Group.group_id == GroupMember.group_id
    ).filter(
        GroupMember.user_id == user_id
    ).all()

    groups = []
    for row in rows:
        groups.append({
            "group_id": row.group_id,
            "role": row.role,
            "group_name": row.group_name,
            "group_icon": row.group_icon
        })

    return {
        "user_id": user_id,
        "groups": groups,
        "total_count": len(groups)
    }


@router.get("/{group_id}/members")
async def get_group_members(
    group_id: int,
    db: Session = Depends(get_db)
):
    """查看小组成员"""
    # 查找小组
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")
    
    # 获取成员列表
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    
    result = []
    for member in members:
        # 获取用户信息
        user = db.query(User).filter(User.user_id == member.user_id).first()
        username = user.username if user else "未知用户"
        
        result.append({
            "user_id": member.user_id,
            "username": username,
            "role": member.role,
            "join_time": member.join_time.isoformat()
        })
    
    return {
        "members": result
    }


@router.post("/{group_id}/messages/send")
async def send_message(
    group_id: int,
    message_data: MessageSend,
    db: Session = Depends(get_db)
):
    """发送消息"""
    # 验证用户是否在小组中
    member = db.query(GroupMember).filter(
        and_(GroupMember.group_id == group_id,
             GroupMember.user_id == message_data.sender_id)
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该小组成员")
    
    # 发送消息
    new_message = GroupMessage(
        group_id=group_id,
        sender_id=message_data.sender_id,
        content=message_data.content,
        message_type=message_data.message_type
    )
    
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    return {
        "success": True,
        "message_id": new_message.message_id,
        "timestamp": new_message.created_at.isoformat()
    }


@router.get("/{group_id}/messages")
async def get_messages(
    group_id: int,
    before: str = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """获取消息"""
    query = db.query(GroupMessage).filter(GroupMessage.group_id == group_id)
    
    if before:
        try:
            before_time = datetime.fromisoformat(before)
            query = query.filter(GroupMessage.created_at < before_time)
        except:
            pass
    
    messages = query.order_by(GroupMessage.created_at.desc()).limit(limit).all()
    messages.reverse()  # 按时间正序返回
    
    result = []
    for message in messages:
        # 获取发送者信息
        user = db.query(User).filter(User.user_id == message.sender_id).first()
        sender_name = user.username if user else "未知用户"
        sender_avatar = ""  # 假设用户表中有头像字段
        
        result.append({
            "message_id": message.message_id,
            "sender_id": message.sender_id,
            "sender_name": sender_name,
            "sender_avatar": sender_avatar,
            "content": message.content,
            "message_type": message.message_type,
            "timestamp": message.created_at.isoformat()
        })
    
    return {
        "messages": result
    }


@router.post("/{group_id}/activity")
async def submit_activity(
    group_id: int,
    activity_data: ActivitySubmit,
    db: Session = Depends(get_db)
):
    """提交学习任务"""
    # 验证用户是否在小组中
    member = db.query(GroupMember).filter(
        and_(GroupMember.group_id == group_id,
             GroupMember.user_id == activity_data.user_id)
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该小组成员")
    
    # 写入activity_log
    new_activity = ActivityLog(
        user_id=activity_data.user_id,
        group_id=group_id,
        activity_type=activity_data.activity_type,
        amount=activity_data.amount
    )
    db.add(new_activity)
    
    # 更新group_task_progress和user_weekly_contribution
    week = get_week_number()
    
    # 更新小组进度
    group_progress = db.query(GroupWeeklyProgress).filter(
        and_(GroupWeeklyProgress.group_id == group_id,
             GroupWeeklyProgress.week == week,
             GroupWeeklyProgress.activity_type == activity_data.activity_type)
    ).first()
    
    if group_progress:
        group_progress.total_amount += activity_data.amount
    else:
        group_progress = GroupWeeklyProgress(
            group_id=group_id,
            week=week,
            activity_type=activity_data.activity_type,
            total_amount=activity_data.amount
        )
        db.add(group_progress)
    
    # 更新个人贡献
    user_contribution = db.query(UserWeeklyContribution).filter(
        and_(UserWeeklyContribution.group_id == group_id,
             UserWeeklyContribution.user_id == activity_data.user_id,
             UserWeeklyContribution.week == week,
             UserWeeklyContribution.activity_type == activity_data.activity_type)
    ).first()
    
    if user_contribution:
        user_contribution.amount += activity_data.amount
    else:
        user_contribution = UserWeeklyContribution(
            group_id=group_id,
            user_id=activity_data.user_id,
            week=week,
            activity_type=activity_data.activity_type,
            amount=activity_data.amount
        )
        db.add(user_contribution)
    
    # 判断任务完成情况并发放金币
    # 这里简化处理，实际应该根据具体任务目标来判断
    
    db.commit()
    
    return {
        "success": True,
        "message": "任务提交成功"
    }


@router.get("/{group_id}/tasks")
async def get_group_tasks(
    group_id: int,
    db: Session = Depends(get_db)
):
    """获取小组任务板信息"""
    # 查找小组
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")
    
    week = get_week_number()
    
    # 获取所有活动类型的进度
    activities = ["listening", "word", "speaking", "forum"]
    tasks = {}
    overall_completed = 0
    overall_target = 0
    
    for activity in activities:
        # 获取小组进度
        group_progress = db.query(GroupWeeklyProgress).filter(
            and_(GroupWeeklyProgress.group_id == group_id,
                 GroupWeeklyProgress.week == week,
                 GroupWeeklyProgress.activity_type == activity)
        ).first()
        
        group_completed = group_progress.total_amount if group_progress else 0
        
        # 这里简化处理，实际应该根据具体任务目标来设置
        goals = [
            {
                "type": "基础",
                "target": 3 if activity == "listening" else 100,
                "completed": group_completed >= (3 if activity == "listening" else 100),
                "reward": {
                    "group": 30,
                    "individual_pool": 60
                }
            },
            {
                "type": "进阶",
                "target": 5 if activity == "listening" else 200,
                "completed": group_completed >= (5 if activity == "listening" else 200),
                "reward": {
                    "group": 10,
                    "individual_pool": 30
                }
            },
            {
                "type": "挑战",
                "target": 8 if activity == "listening" else 300,
                "completed": group_completed >= (8 if activity == "listening" else 300),
                "reward": {
                    "group": 20,
                    "individual_pool": 40
                }
            }
        ]
        
        # 计算总目标和已完成
        for goal in goals:
            overall_target += goal["target"]
            if goal["completed"]:
                overall_completed += goal["target"]
        
        tasks[activity] = {
            "group_completed": group_completed,
            "my_contribution": 0,  # 需要从认证中获取用户ID并查询
            "goals": goals
        }
    
    # 计算总体进度
    completion_percent = int((overall_completed / overall_target) * 100) if overall_target > 0 else 0
    
    return {
        "group_id": group_id,
        "week": week,
        "overall_progress": {
            "completion_percent": completion_percent
        },
        "tasks": tasks
    }


@router.get("/{group_id}/my_stats")
async def get_my_stats(
    group_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """获取个人贡献"""
    # 验证用户是否在小组中
    member = db.query(GroupMember).filter(
        and_(GroupMember.group_id == group_id,
             GroupMember.user_id == user_id)
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="您不是该小组成员")
    
    week = get_week_number()
    
    # 获取个人贡献
    contributions = db.query(UserWeeklyContribution).filter(
        and_(UserWeeklyContribution.group_id == group_id,
             UserWeeklyContribution.user_id == user_id,
             UserWeeklyContribution.week == week)
    ).all()
    
    contribution_dict = {}
    for contrib in contributions:
        contribution_dict[contrib.activity_type] = contrib.amount
    
    # 获取本周获得的金币
    coins_earned = db.query(func.sum(RewardLog.coins)).filter(
        and_(RewardLog.user_id == user_id,
             RewardLog.group_id == group_id,
             RewardLog.status == 1)
    ).scalar() or 0
    
    # 计算组内排名
    # 这里简化处理，实际应该根据贡献总量计算
    rank_in_group = 1
    
    return {
        "user_id": user_id,
        "contribution": contribution_dict,
        "coins_earned_this_week": coins_earned,
        "rank_in_group": rank_in_group
    }
