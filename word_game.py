from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import random
import uuid
import json

from database import get_db

router = APIRouter(prefix="/wordgame", tags=["Word Game"])


# =========================================================
# 工具函数
# =========================================================
def generate_match_code() -> str:
    return str(uuid.uuid4()).replace("-", "")[:8].upper()


def create_event(db: Session, match_id: int, event_type: str, user_id: int = None, event_data: dict = None):
    db.execute(
        text("""
            INSERT INTO t_wordgame_event (
                match_id, user_id, event_type, event_data, created_at
            ) VALUES (
                :match_id, :user_id, :event_type, :event_data, NOW()
            )
        """),
        {
            "match_id": match_id,
            "user_id": user_id,
            "event_type": event_type,
            "event_data": json.dumps(event_data, ensure_ascii=False) if event_data else None
        }
    )


def get_user_active_match(db: Session, user_id: int):
    return db.execute(
        text("""
            SELECT
                p.id AS player_id,
                p.match_id,
                p.user_id,
                p.seat_no,
                p.team,
                p.member_no,
                p.status AS player_status,
                CASE
                    WHEN p.roll_count_date = CURDATE() THEN p.today_roll_contribute
                    ELSE 0
                END AS today_roll_contribute,
                p.total_roll_contribute,
                m.match_code,
                m.status AS match_status,
                m.max_players,
                m.current_players,
                m.total_cells,
                m.red_position,
                m.blue_position,
                m.red_available_rolls,
                m.blue_available_rolls,
                m.winner_team
            FROM t_wordgame_match_player p
            JOIN t_wordgame_match m ON p.match_id = m.id
            WHERE p.user_id = :user_id
              AND p.status IN ('matching', 'active')
              AND m.status IN ('waiting', 'active')
            ORDER BY p.joined_at DESC
            LIMIT 1
        """),
        {"user_id": user_id}
    ).mappings().first()


def get_user_latest_match(db: Session, user_id: int):
    return db.execute(
        text("""
            SELECT
                p.id AS player_id,
                p.match_id,
                p.user_id,
                p.seat_no,
                p.team,
                p.member_no,
                p.status AS player_status,
                CASE
                    WHEN p.roll_count_date = CURDATE() THEN p.today_roll_contribute
                    ELSE 0
                END AS today_roll_contribute,
                p.total_roll_contribute,
                m.match_code,
                m.status AS match_status,
                m.max_players,
                m.current_players,
                m.total_cells,
                m.red_position,
                m.blue_position,
                m.red_available_rolls,
                m.blue_available_rolls,
                m.winner_team,
                m.finished_at
            FROM t_wordgame_match_player p
            JOIN t_wordgame_match m ON p.match_id = m.id
            WHERE p.user_id = :user_id
            ORDER BY
                CASE
                    WHEN m.status IN ('waiting', 'active') THEN 0
                    WHEN m.status = 'finished' THEN 1
                    ELSE 2
                END,
                COALESCE(m.finished_at, m.created_at) DESC,
                p.joined_at DESC
            LIMIT 1
        """),
        {"user_id": user_id}
    ).mappings().first()


def get_waiting_match(db: Session):
    return db.execute(
        text("""
            SELECT *
            FROM t_wordgame_match
            WHERE status = 'waiting'
              AND current_players < max_players
            ORDER BY created_at ASC
            LIMIT 1
        """)
    ).mappings().first()


def create_match(db: Session, user_id: int):
    match_code = generate_match_code()

    db.execute(
        text("""
            INSERT INTO t_wordgame_match (
                match_code, status, max_players, current_players, total_cells,
                red_position, blue_position,
                red_available_rolls, blue_available_rolls,
                winner_team, created_by, created_at
            ) VALUES (
                :match_code, 'waiting', 4, 0, 84,
                0, 0,
                0, 0,
                NULL, :created_by, NOW()
            )
        """),
        {
            "match_code": match_code,
            "created_by": user_id
        }
    )

    match = db.execute(
        text("""
            SELECT *
            FROM t_wordgame_match
            WHERE match_code = :match_code
            LIMIT 1
        """),
        {"match_code": match_code}
    ).mappings().first()

    create_event(db, match["id"], "match_created", user_id, {
        "match_code": match_code
    })

    return match


def assign_teams_and_start_if_full(db: Session, match_id: int):
    players = db.execute(
        text("""
            SELECT id, user_id, seat_no
            FROM t_wordgame_match_player
            WHERE match_id = :match_id
            ORDER BY seat_no ASC
        """),
        {"match_id": match_id}
    ).mappings().all()

    if len(players) != 4:
        return False

    # 固定座位分队：
    # 1,2 -> red
    # 3,4 -> blue
    team_map = {
        1: ("red", 1),
        2: ("red", 2),
        3: ("blue", 1),
        4: ("blue", 2),
    }

    for p in players:
        team, member_no = team_map[p["seat_no"]]
        db.execute(
            text("""
                UPDATE t_wordgame_match_player
                SET team = :team,
                    member_no = :member_no,
                    status = 'active'
                WHERE id = :player_id
            """),
            {
                "team": team,
                "member_no": member_no,
                "player_id": p["id"]
            }
        )

    db.execute(
        text("""
            UPDATE t_wordgame_match
            SET status = 'active',
                started_at = NOW()
            WHERE id = :match_id
        """),
        {"match_id": match_id}
    )

    create_event(db, match_id, "match_started", None, {
        "players": 4
    })

    return True


def get_match_players(db: Session, match_id: int):
    return db.execute(
        text("""
            SELECT
                id,
                match_id,
                user_id,
                seat_no,
                team,
                member_no,
                status,
                joined_at,
                left_at,
                CASE
                    WHEN roll_count_date = CURDATE() THEN today_roll_contribute
                    ELSE 0
                END AS today_roll_contribute,
                total_roll_contribute
            FROM t_wordgame_match_player
            WHERE match_id = :match_id
            ORDER BY seat_no ASC
        """),
        {"match_id": match_id}
    ).mappings().all()


def get_match_detail(db: Session, match_id: int):
    match = db.execute(
        text("""
            SELECT *
            FROM t_wordgame_match
            WHERE id = :match_id
            LIMIT 1
        """),
        {"match_id": match_id}
    ).mappings().first()

    if not match:
        return None

    players = get_match_players(db, match_id)

    return {
        "id": match["id"],
        "match_code": match["match_code"],
        "status": match["status"],
        "max_players": match["max_players"],
        "current_players": match["current_players"],
        "total_cells": match["total_cells"],
        "red_position": match["red_position"],
        "blue_position": match["blue_position"],
        "red_available_rolls": match["red_available_rolls"],
        "blue_available_rolls": match["blue_available_rolls"],
        "winner_team": match["winner_team"],
        "created_by": match["created_by"],
        "created_at": match["created_at"],
        "started_at": match["started_at"],
        "finished_at": match["finished_at"],
        "players": [dict(p) for p in players]
    }


# =========================================================
# 接口
# =========================================================
@router.post("/join")
def join_game(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_match(db, user_id)
    if existing:
        return {
            "message": "already joined",
            "match_id": existing["match_id"],
            "match_code": existing["match_code"],
            "status": existing["match_status"]
        }

    match = get_waiting_match(db)
    if not match:
        match = create_match(db, user_id)

    used_seats = db.execute(
        text("""
            SELECT seat_no
            FROM t_wordgame_match_player
            WHERE match_id = :match_id
            AND status IN ('matching', 'active')
            ORDER BY seat_no
        """),
        {"match_id": match["id"]}
    ).mappings().all()

    used = {row["seat_no"] for row in used_seats}
    next_seat = next(seat for seat in range(1, 5) if seat not in used)

    db.execute(
        text("""
            INSERT INTO t_wordgame_match_player (
                match_id, user_id, seat_no, team, member_no, status,
                joined_at, today_roll_contribute, total_roll_contribute, roll_count_date
            ) VALUES (
                :match_id, :user_id, :seat_no, NULL, NULL, 'matching',
                NOW(), 0, 0, NULL
            )
        """),
        {
            "match_id": match["id"],
            "user_id": user_id,
            "seat_no": next_seat
        }
    )

    db.execute(
        text("""
            UPDATE t_wordgame_match
            SET current_players = current_players + 1
            WHERE id = :match_id
        """),
        {"match_id": match["id"]}
    )

    create_event(db, match["id"], "player_joined", user_id, {
        "seat_no": next_seat
    })

    updated_match = db.execute(
        text("""
            SELECT *
            FROM t_wordgame_match
            WHERE id = :match_id
            LIMIT 1
        """),
        {"match_id": match["id"]}
    ).mappings().first()

    if updated_match["current_players"] == updated_match["max_players"]:
        assign_teams_and_start_if_full(db, updated_match["id"])

    db.commit()

    final_match = db.execute(
        text("""
            SELECT *
            FROM t_wordgame_match
            WHERE id = :match_id
            LIMIT 1
        """),
        {"match_id": match["id"]}
    ).mappings().first()

    return {
        "match_id": final_match["id"],
        "match_code": final_match["match_code"],
        "status": final_match["status"],
        "players": final_match["current_players"]
    }


@router.post("/cancel")
def cancel_match(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_match(db, user_id)
    if not existing:
        return {"message": "not in match"}

    if existing["match_status"] != "waiting":
        raise HTTPException(status_code=400, detail="cannot cancel after game started")

    db.execute(
        text("""
            UPDATE t_wordgame_match_player
            SET status = 'cancelled',
                left_at = NOW()
            WHERE id = :player_id
        """),
        {"player_id": existing["player_id"]}
    )

    db.execute(
        text("""
            UPDATE t_wordgame_match
            SET current_players = CASE
                WHEN current_players > 0 THEN current_players - 1
                ELSE 0
            END
            WHERE id = :match_id
        """),
        {"match_id": existing["match_id"]}
    )

    create_event(db, existing["match_id"], "player_cancelled", user_id, None)

    remaining = db.execute(
        text("""
            SELECT COUNT(*) AS cnt
            FROM t_wordgame_match_player
            WHERE match_id = :match_id
              AND status IN ('matching', 'active')
        """),
        {"match_id": existing["match_id"]}
    ).mappings().first()

    if remaining["cnt"] == 0:
        db.execute(
            text("""
                UPDATE t_wordgame_match
                SET status = 'finished',
                    finished_at = NOW()
                WHERE id = :match_id
            """),
            {"match_id": existing["match_id"]}
        )
        create_event(db, existing["match_id"], "match_closed_empty", None, None)

    db.commit()
    return {"message": "cancelled"}


@router.get("/status")
def get_status(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_match(db, user_id)

    if existing:
        match_detail = get_match_detail(db, existing["match_id"])
        return {
            "in_match": True,
            "match": match_detail,
            "last_match": None
        }

    latest = get_user_latest_match(db, user_id)
    if latest and latest["match_status"] == "finished":
        match_detail = get_match_detail(db, latest["match_id"])
        return {
            "in_match": False,
            "match": None,
            "last_match": match_detail
        }

    return {
        "in_match": False,
        "match": None,
        "last_match": None
    }


@router.get("/quiz-question")
def get_quiz_question(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_match(db, user_id)
    if not existing:
        raise HTTPException(status_code=400, detail="not in match")

    if existing["match_status"] != "active":
        raise HTTPException(status_code=400, detail="match is not active")

    row = db.execute(
        text("""
            SELECT
                word_id,
                subcategory_id,
                english,
                explanation,
                create_time
            FROM t_word
            WHERE english IS NOT NULL
              AND explanation IS NOT NULL
              AND TRIM(english) <> ''
              AND TRIM(explanation) <> ''
            ORDER BY RAND()
            LIMIT 1
        """)
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="no question found")

    return {
        "word_id": row["word_id"],
        "subcategory_id": row["subcategory_id"],
        "question": row["explanation"],
        "answer": row["english"],   # 测试阶段先返回答案
        "message": "question loaded"
    }


@router.post("/gain-roll")
def gain_roll(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_match(db, user_id)
    if not existing:
        raise HTTPException(status_code=400, detail="not in match")

    if existing["match_status"] != "active":
        raise HTTPException(status_code=400, detail="match is not active")

    if existing["team"] not in ("red", "blue"):
        raise HTTPException(status_code=400, detail="team not assigned")

    # 读取玩家原始计数（不经过 CASE 包装）
    player_row = db.execute(
        text("""
            SELECT
                id,
                today_roll_contribute,
                total_roll_contribute,
                roll_count_date
            FROM t_wordgame_match_player
            WHERE id = :player_id
            LIMIT 1
        """),
        {"player_id": existing["player_id"]}
    ).mappings().first()

    if not player_row:
        raise HTTPException(status_code=404, detail="player not found")

    today = datetime.now().date()

    # 如果不是今天，则先重置 today_roll_contribute
    if player_row["roll_count_date"] != today:
        db.execute(
            text("""
                UPDATE t_wordgame_match_player
                SET today_roll_contribute = 0,
                    roll_count_date = CURDATE()
                WHERE id = :player_id
            """),
            {"player_id": existing["player_id"]}
        )
        current_today_count = 0
    else:
        current_today_count = player_row["today_roll_contribute"] or 0

    # 每人每天最多成功获得 3 次 roll
    if current_today_count >= 3:
        db.rollback()
        raise HTTPException(status_code=400, detail="daily roll gain limit reached (max 3)")

    db.execute(
        text("""
            UPDATE t_wordgame_match_player
            SET today_roll_contribute = today_roll_contribute + 1,
                total_roll_contribute = total_roll_contribute + 1,
                roll_count_date = CURDATE()
            WHERE id = :player_id
        """),
        {"player_id": existing["player_id"]}
    )

    if existing["team"] == "red":
        db.execute(
            text("""
                UPDATE t_wordgame_match
                SET red_available_rolls = red_available_rolls + 1
                WHERE id = :match_id
            """),
            {"match_id": existing["match_id"]}
        )
    else:
        db.execute(
            text("""
                UPDATE t_wordgame_match
                SET blue_available_rolls = blue_available_rolls + 1
                WHERE id = :match_id
            """),
            {"match_id": existing["match_id"]}
        )

    create_event(db, existing["match_id"], "gain_roll", user_id, {
        "team": existing["team"]
    })

    db.commit()

    match = db.execute(
        text("""
            SELECT red_available_rolls, blue_available_rolls
            FROM t_wordgame_match
            WHERE id = :match_id
        """),
        {"match_id": existing["match_id"]}
    ).mappings().first()

    remaining = 2 - current_today_count

    return {
        "message": "roll gained",
        "team": existing["team"],
        "red_available_rolls": match["red_available_rolls"],
        "blue_available_rolls": match["blue_available_rolls"],
        "today_roll_contribute": current_today_count + 1,
        "remaining_gain_times_today": remaining
    }


@router.post("/roll")
def roll(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_match(db, user_id)
    if not existing:
        raise HTTPException(status_code=400, detail="not in match")

    if existing["match_status"] != "active":
        raise HTTPException(status_code=400, detail="match is not active")

    if existing["team"] not in ("red", "blue"):
        raise HTTPException(status_code=400, detail="team not assigned")

    step = random.randint(1, 6)

    match = db.execute(
        text("""
            SELECT *
            FROM t_wordgame_match
            WHERE id = :match_id
            LIMIT 1
        """),
        {"match_id": existing["match_id"]}
    ).mappings().first()

    if existing["team"] == "red":
        if match["red_available_rolls"] <= 0:
            raise HTTPException(status_code=400, detail="no rolls")

        new_pos = match["red_position"] + step
        finished = new_pos >= (match["total_cells"] - 1)
        if finished:
            new_pos = match["total_cells"] - 1

        db.execute(
            text("""
                UPDATE t_wordgame_match
                SET red_available_rolls = red_available_rolls - 1,
                    red_position = :new_pos,
                    status = CASE WHEN :finished = 1 THEN 'finished' ELSE status END,
                    winner_team = CASE WHEN :finished = 1 THEN 'red' ELSE winner_team END,
                    finished_at = CASE WHEN :finished = 1 THEN NOW() ELSE finished_at END
                WHERE id = :match_id
            """),
            {
                "new_pos": new_pos,
                "finished": 1 if finished else 0,
                "match_id": existing["match_id"]
            }
        )

    else:
        if match["blue_available_rolls"] <= 0:
            raise HTTPException(status_code=400, detail="no rolls")

        new_pos = match["blue_position"] + step
        finished = new_pos >= (match["total_cells"] - 1)
        if finished:
            new_pos = match["total_cells"] - 1

        db.execute(
            text("""
                UPDATE t_wordgame_match
                SET blue_available_rolls = blue_available_rolls - 1,
                    blue_position = :new_pos,
                    status = CASE WHEN :finished = 1 THEN 'finished' ELSE status END,
                    winner_team = CASE WHEN :finished = 1 THEN 'blue' ELSE winner_team END,
                    finished_at = CASE WHEN :finished = 1 THEN NOW() ELSE finished_at END
                WHERE id = :match_id
            """),
            {
                "new_pos": new_pos,
                "finished": 1 if finished else 0,
                "match_id": existing["match_id"]
            }
        )

    create_event(db, existing["match_id"], "roll", user_id, {
        "team": existing["team"],
        "step": step
    })

    if finished:
        db.execute(
            text("""
                UPDATE t_wordgame_match_player
                SET status = 'finished'
                WHERE match_id = :match_id
                  AND status = 'active'
            """),
            {"match_id": existing["match_id"]}
        )

        create_event(db, existing["match_id"], "match_finished", user_id, {
            "winner_team": existing["team"]
        })

    db.commit()

    updated = db.execute(
        text("""
            SELECT
                red_position, blue_position,
                red_available_rolls, blue_available_rolls,
                status, winner_team
            FROM t_wordgame_match
            WHERE id = :match_id
        """),
        {"match_id": existing["match_id"]}
    ).mappings().first()

    return {
        "step": step,
        "team": existing["team"],
        "red_position": updated["red_position"],
        "blue_position": updated["blue_position"],
        "red_available_rolls": updated["red_available_rolls"],
        "blue_available_rolls": updated["blue_available_rolls"],
        "status": updated["status"],
        "winner_team": updated["winner_team"]
    }