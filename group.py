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
from pydantic import Field


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
    group_type = Column(String(20))
    title = Column(String(100))
    description = Column(String(500))
    cover_image = Column(String(255))
    study_types = Column(String(100))


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

#新加了两个表
class GroupImage(Base):
    __tablename__ = "t_group_image"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False)
    image_url = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class GroupTask(Base):
    __tablename__ = "t_group_task"

    task_id = Column(BigInteger, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=False)
    activity_type = Column(String(20), nullable=False)
    target_amount = Column(Integer, nullable=False)
    reward_coins = Column(Integer, default=50)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    created_by = Column(BigInteger)


# Pydantic模型
class GroupCreate(BaseModel):
    user_id: int
    group_name: str
    max_members: int
    group_icon: str = None
    password: str = None

    # 新增 ↓↓↓
    group_type: str = "study"  # study / social
    title: str = None
    description: str = None
    study_types: str = None  # "word,listening"
    cover_image: str = None

    images: list[str] = Field(default_factory=list)


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

class TaskCreate(BaseModel):
    user_id: int
    activity_type: str      # word / listening / speaking / forum
    target_amount: int
    reward_coins: int = 50
    start_date: datetime
    end_date: datetime


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
    query = db.query(Group)

    if search:
        query = query.filter(Group.group_name.contains(search))

    total_count = query.count()
    groups = query.offset((page - 1) * page_size).limit(page_size).all()

    result = []

    for group in groups:
        current_members = db.query(GroupMember).filter(
            GroupMember.group_id == group.group_id
        ).count()

        # ⭐ 核心：查多图
        images = db.query(GroupImage).filter(
            GroupImage.group_id == group.group_id
        ).all()

        image_list = [img.image_url for img in images]

        result.append({
            "group_id": group.group_id,
            "group_name": group.group_name,
            "title": group.title,
            "description": group.description,
            "group_type": group.group_type,
            "study_types": group.study_types,
            "cover_image": group.cover_image,

            "images": image_list,  # ⭐ 多图就在这里

            "current_members": current_members,
            "max_members": group.max_members,
            "group_icon": group.group_icon,
            "creator_id": group.creator_id,
            "has_password": group.password is not None
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
    """创建小组（支持多图 + 安全版）"""

    # 1. 校验
    if group_data.max_members < 2 or group_data.max_members > 20:
        raise HTTPException(status_code=400, detail="小组人数必须在2-20之间")

    if group_data.group_type not in ["study", "social"]:
        raise HTTPException(status_code=400, detail="group_type必须是 study 或 social")

    if group_data.group_type == "study" and not group_data.study_types:
        raise HTTPException(status_code=400, detail="学习型小组必须选择学习类型")

    try:
        # 2. 创建 group
        new_group = Group(
            group_name=group_data.group_name,
            creator_id=group_data.user_id,
            max_members=group_data.max_members,
            group_icon=group_data.group_icon,
            password=hash_password(group_data.password),

            group_type=group_data.group_type,
            title=group_data.title,
            description=group_data.description,
            study_types=group_data.study_types,
            cover_image=group_data.cover_image
        )

        db.add(new_group)
        db.flush()  # ⭐ 关键：拿到 group_id，但不提交

        # 3. 创建者加入
        db.add(GroupMember(
            group_id=new_group.group_id,
            user_id=new_group.creator_id,
            role="leader"
        ))

        # 4. 插入多图（带校验）
        if group_data.images:
            for img_url in group_data.images:
                if not img_url:
                    continue  # 跳过空值

                db.add(GroupImage(
                    group_id=new_group.group_id,
                    image_url=img_url
                ))

        # 5. 一次性提交（事务安全）
        db.commit()

        return {
            "success": True,
            "group_id": new_group.group_id,
            "image_count": len(group_data.images),
            "message": "小组创建成功（含图片）"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"创建失败: {str(e)}")



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

@router.post("/{group_id}/tasks/create")
async def create_task(
    group_id: int,
    task_data: TaskCreate,
    db: Session = Depends(get_db)
):
    """创建小组任务（只有leader可以创建）"""

    # 1. 检查小组是否存在
    group = db.query(Group).filter(Group.group_id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="小组不存在")

    # 2. 检查用户是否是leader
    member = db.query(GroupMember).filter(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == task_data.user_id
        )
    ).first()

    if not member or member.role != "leader":
        raise HTTPException(status_code=403, detail="只有组长可以创建任务")

    # 3. 检查 activity_type 是否合法
    valid_types = ["word", "listening", "speaking", "forum"]
    if task_data.activity_type not in valid_types:
        raise HTTPException(status_code=400, detail="无效的任务类型")

    # 4. 创建任务
    new_task = GroupTask(
        group_id=group_id,
        activity_type=task_data.activity_type,
        target_amount=task_data.target_amount,
        reward_coins=task_data.reward_coins,
        start_date=task_data.start_date,
        end_date=task_data.end_date,
        created_by=task_data.user_id
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return {
        "success": True,
        "task_id": new_task.task_id,
        "message": "任务创建成功"
    }

#检测任务是否完成
def check_and_give_reward(db, group_id, activity_type):
    """检查任务是否完成，如果完成则发奖励"""

    week = get_week_number()

    # 1. 找到当前任务
    task = db.query(GroupTask).filter(
        and_(
            GroupTask.group_id == group_id,
            GroupTask.activity_type == activity_type
        )
    ).first()

    if not task:
        return

    # 2. 找到小组当前进度
    progress = db.query(GroupWeeklyProgress).filter(
        and_(
            GroupWeeklyProgress.group_id == group_id,
            GroupWeeklyProgress.week == week,
            GroupWeeklyProgress.activity_type == activity_type
        )
    ).first()

    if not progress:
        return

    # 3. 判断是否完成任务
    if progress.total_amount < task.target_amount:
        return

    # 4. 检查是否已经发过奖励（防止重复发）
    existing_reward = db.query(RewardLog).filter(
        and_(
            RewardLog.group_id == group_id,
            RewardLog.activity_type == activity_type,
            RewardLog.goal_type == "task_complete"
        )
    ).first()

    if existing_reward:
        return  # 已经发过奖励了

    # 5. 获取所有成员
    members = db.query(GroupMember).filter(
        GroupMember.group_id == group_id
    ).all()

    if not members:
        return

    # 6. 平均发奖励
    reward_per_user = int(task.reward_coins / len(members))

    for member in members:
        # 写 reward_log
        reward = RewardLog(
            user_id=member.user_id,
            group_id=group_id,
            activity_type=activity_type,
            goal_type="task_complete",
            coins=reward_per_user,
            status=1
        )
        db.add(reward)

        # 更新用户金币
        user = db.query(User).filter(User.user_id == member.user_id).first()
        if user:
            user.points += reward_per_user

    db.commit()


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

@router.post("/{group_id}/activity")
async def submit_activity(
    group_id: int,
    activity_data: ActivitySubmit,
    db: Session = Depends(get_db)
):
    """提交学习任务 + 自动计算奖励"""

    # 1. 验证用户是否在小组中
    member = db.query(GroupMember).filter(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.user_id == activity_data.user_id
        )
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="您不是该小组成员")

    # 2. 写入 activity_log
    new_activity = ActivityLog(
        user_id=activity_data.user_id,
        group_id=group_id,
        activity_type=activity_data.activity_type,
        amount=activity_data.amount
    )
    db.add(new_activity)

    week = get_week_number()

    # 3. 更新小组进度
    group_progress = db.query(GroupWeeklyProgress).filter(
        and_(
            GroupWeeklyProgress.group_id == group_id,
            GroupWeeklyProgress.week == week,
            GroupWeeklyProgress.activity_type == activity_data.activity_type
        )
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

    # 4. 更新个人贡献
    user_contribution = db.query(UserWeeklyContribution).filter(
        and_(
            UserWeeklyContribution.group_id == group_id,
            UserWeeklyContribution.user_id == activity_data.user_id,
            UserWeeklyContribution.week == week,
            UserWeeklyContribution.activity_type == activity_data.activity_type
        )
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

    db.commit()

    # 5. ⭐ 提交后检查是否完成任务 → 发奖励
    check_and_give_reward(db, group_id, activity_data.activity_type)

    return {
        "success": True,
        "message": "任务提交成功"
    }

@router.get("/{group_id}/tasks")
async def get_group_tasks(group_id: int, db: Session = Depends(get_db)):
    """获取小组任务 + 当前进度"""

    week = get_week_number()

    # 1. 获取所有任务
    tasks = db.query(GroupTask).filter(
        GroupTask.group_id == group_id
    ).all()

    result = []

    for task in tasks:
        # 2. 获取当前进度
        progress = db.query(GroupWeeklyProgress).filter(
            and_(
                GroupWeeklyProgress.group_id == group_id,
                GroupWeeklyProgress.week == week,
                GroupWeeklyProgress.activity_type == task.activity_type
            )
        ).first()

        current_amount = progress.total_amount if progress else 0

        result.append({
            "task_id": task.task_id,
            "activity_type": task.activity_type,
            "target_amount": task.target_amount,
            "current_amount": current_amount,
            "reward_coins": task.reward_coins,
            "start_date": task.start_date,
            "end_date": task.end_date
        })

    return result

@router.get("/{group_id}/ranking")
async def get_group_ranking(group_id: int, db: Session = Depends(get_db)):
    """获取小组本周贡献排行榜"""

    week = get_week_number()

    ranking = db.query(
        UserWeeklyContribution.user_id,
        func.sum(UserWeeklyContribution.amount).label("total_amount")
    ).filter(
        and_(
            UserWeeklyContribution.group_id == group_id,
            UserWeeklyContribution.week == week
        )
    ).group_by(
        UserWeeklyContribution.user_id
    ).order_by(
        func.sum(UserWeeklyContribution.amount).desc()
    ).all()

    result = []
    rank = 1

    for r in ranking:
        # 查用户名
        user = db.query(User).filter(User.user_id == r.user_id).first()

        result.append({
            "rank": rank,
            "user_id": r.user_id,
            "username": user.username if user else "Unknown",
            "total_contribution": r.total_amount
        })

        rank += 1

    return result

@router.post("/upload_images")
async def upload_images(
    request: Request,
    images: list[str] = Form(...),  # base64 list
):
    """上传多张图片（base64）并返回URL列表"""

    if not images:
        raise HTTPException(status_code=400, detail="图片列表不能为空")

    uploaded_urls = []

    for image_base64 in images:
        try:
            image_bytes, suffix = decode_base64_image(image_base64)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        filename = f"group_img_{uuid.uuid4().hex}{suffix}"
        file_path = GROUP_HEAD_DIR / filename
        file_path.write_bytes(image_bytes)

        base_url = str(request.base_url).rstrip("/")
        image_url = f"{base_url}/{GROUP_HEAD_BASE_PATH}/{filename}"

        uploaded_urls.append(image_url)

    return {
        "success": True,
        "images": uploaded_urls
    }
