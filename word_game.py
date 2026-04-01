from fastapi import APIRouter, HTTPException
from typing import Dict, List
import uuid
import random

router = APIRouter(prefix="/wordgame", tags=["Word Game"])

# =========================
# 内存数据（第一阶段先这样）
# =========================
matches: Dict[str, dict] = {}
user_match: Dict[int, str] = {}  # user_id -> match_id


# =========================
# 工具函数
# =========================
def get_waiting_match():
    for m in matches.values():
        if m["status"] == "waiting" and len(m["players"]) < 4:
            return m
    return None


def create_match(user_id: int):
    match_id = str(uuid.uuid4())[:8]
    match = {
        "id": match_id,
        "status": "waiting",
        "players": [],
        "red_pos": 0,
        "blue_pos": 0,
        "red_rolls": 0,
        "blue_rolls": 0,
        "winner": None
    }
    matches[match_id] = match
    return match


def assign_teams(match):
    players = match["players"]
    # 固定分组
    players[0]["team"] = "red"
    players[1]["team"] = "red"
    players[2]["team"] = "blue"
    players[3]["team"] = "blue"


# =========================
# 接口
# =========================

@router.post("/join")
def join_game(user_id: int):
    # 已经在局中
    if user_id in user_match:
        match_id = user_match[user_id]
        return {"message": "already joined", "match_id": match_id}

    match = get_waiting_match()
    if not match:
        match = create_match(user_id)

    # 加入
    player = {
        "user_id": user_id,
        "team": None,
        "roll_contribute": 0
    }
    match["players"].append(player)
    user_match[user_id] = match["id"]

    # 满4人开局
    if len(match["players"]) == 4:
        match["status"] = "active"
        assign_teams(match)

    return {
        "match_id": match["id"],
        "status": match["status"],
        "players": len(match["players"])
    }


@router.post("/cancel")
def cancel_match(user_id: int):
    if user_id not in user_match:
        return {"message": "not in match"}

    match_id = user_match[user_id]
    match = matches[match_id]

    if match["status"] != "waiting":
        raise HTTPException(400, "cannot cancel after game started")

    match["players"] = [p for p in match["players"] if p["user_id"] != user_id]
    del user_match[user_id]

    return {"message": "cancelled"}


@router.get("/status")
def get_status(user_id: int):
    if user_id not in user_match:
        return {"in_match": False}

    match = matches[user_match[user_id]]

    return {
        "in_match": True,
        "match": match
    }


@router.post("/gain-roll")
def gain_roll(user_id: int):
    if user_id not in user_match:
        raise HTTPException(400, "not in match")

    match = matches[user_match[user_id]]

    player = next(p for p in match["players"] if p["user_id"] == user_id)
    player["roll_contribute"] += 1

    if player["team"] == "red":
        match["red_rolls"] += 1
    else:
        match["blue_rolls"] += 1

    return {"message": "roll gained"}


@router.post("/roll")
def roll(user_id: int):
    match = matches[user_match[user_id]]

    player = next(p for p in match["players"] if p["user_id"] == user_id)

    if player["team"] == "red":
        if match["red_rolls"] <= 0:
            raise HTTPException(400, "no rolls")
        match["red_rolls"] -= 1
        step = random.randint(1, 6)
        match["red_pos"] += step
        if match["red_pos"] >= 83:
            match["winner"] = "red"
            match["status"] = "finished"
    else:
        if match["blue_rolls"] <= 0:
            raise HTTPException(400, "no rolls")
        match["blue_rolls"] -= 1
        step = random.randint(1, 6)
        match["blue_pos"] += step
        if match["blue_pos"] >= 83:
            match["winner"] = "blue"
            match["status"] = "finished"

    return {"step": step}