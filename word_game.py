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
# Constants
# =========================================================
MULTI_WIN_REWARD = 80
MULTI_LOSE_REWARD = 30
SINGLE_TOTAL_CELLS = 84
SINGLE_DAILY_GAIN_LIMIT = 3
SINGLE_REWARD_RULES = [
    {"key": "day1_cell10", "target_day": 1, "target_cell": 10, "points": 20, "title": "Day 1 Explorer"},
    {"key": "day2_cell20", "target_day": 2, "target_cell": 20, "points": 30, "title": "Day 2 Runner"},
    {"key": "day3_cell35", "target_day": 3, "target_cell": 35, "points": 50, "title": "Day 3 Challenger"},
]
SINGLE_FINISH_REWARD = {"key": "finish", "points": 100, "title": "Single Mode Completion"}


# =========================================================
# Generic helpers
# =========================================================
def _safe_json_loads(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _single_game_day(started_at) -> int:
    if not started_at:
        return 1
    try:
        delta = datetime.now().date() - started_at.date()
        return max(1, delta.days + 1)
    except Exception:
        return 1


def _random_question_row(db: Session):
    return db.execute(
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


def _get_user_points(db: Session, user_id: int) -> int:
    row = db.execute(
        text("""
            SELECT points
            FROM t_user
            WHERE user_id = :user_id
              AND (is_delete = 0 OR is_delete IS NULL)
            LIMIT 1
        """),
        {"user_id": user_id}
    ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return row.get("points", 0) or 0


def _add_user_points(db: Session, user_id: int, points: int):
    if not points:
        return
    result = db.execute(
        text("""
            UPDATE t_user
            SET points = COALESCE(points, 0) + :points,
                update_time = NOW()
            WHERE user_id = :user_id
              AND (is_delete = 0 OR is_delete IS NULL)
        """),
        {"user_id": user_id, "points": points}
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="user not found")


# =========================================================
# Multiplayer helpers
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


def _get_multi_reward_claim_map(db: Session, match_id: int):
    rows = db.execute(
        text("""
            SELECT user_id, result, points, title, created_at
            FROM t_wordgame_multi_reward_claim
            WHERE match_id = :match_id
        """),
        {"match_id": match_id}
    ).mappings().all()
    return {r["user_id"]: dict(r) for r in rows}


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
    reward_claims = _get_multi_reward_claim_map(db, match_id)

    players_payload = []
    for p in players:
        item = dict(p)
        reward_claim = reward_claims.get(p["user_id"])
        item["reward_claim"] = reward_claim
        players_payload.append(item)

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
        "players": players_payload,
        "reward_rules": {
            "win_points": MULTI_WIN_REWARD,
            "lose_points": MULTI_LOSE_REWARD,
        }
    }


def _grant_multi_rewards_if_needed(db: Session, match_id: int, winner_team: str):
    players = db.execute(
        text("""
            SELECT user_id, team
            FROM t_wordgame_match_player
            WHERE match_id = :match_id
              AND team IN ('red', 'blue')
        """),
        {"match_id": match_id}
    ).mappings().all()

    granted_payload = []
    for p in players:
        existed = db.execute(
            text("""
                SELECT id, points, result, title
                FROM t_wordgame_multi_reward_claim
                WHERE match_id = :match_id
                  AND user_id = :user_id
                LIMIT 1
            """),
            {"match_id": match_id, "user_id": p["user_id"]}
        ).mappings().first()

        if existed:
            granted_payload.append({
                "user_id": p["user_id"],
                "team": p["team"],
                "result": existed["result"],
                "points": existed["points"],
                "title": existed["title"],
            })
            continue

        result = "win" if p["team"] == winner_team else "lose"
        points = MULTI_WIN_REWARD if result == "win" else MULTI_LOSE_REWARD
        title = "Multiplayer Victory Reward" if result == "win" else "Multiplayer Participation Reward"

        db.execute(
            text("""
                INSERT INTO t_wordgame_multi_reward_claim (
                    match_id, user_id, team, result, points, title, created_at
                ) VALUES (
                    :match_id, :user_id, :team, :result, :points, :title, NOW()
                )
            """),
            {
                "match_id": match_id,
                "user_id": p["user_id"],
                "team": p["team"],
                "result": result,
                "points": points,
                "title": title,
            }
        )
        _add_user_points(db, p["user_id"], points)
        granted_payload.append({
            "user_id": p["user_id"],
            "team": p["team"],
            "result": result,
            "points": points,
            "title": title,
        })

    return granted_payload


# =========================================================
# Single-player helpers
# =========================================================
def get_user_active_single_game(db: Session, user_id: int):
    return db.execute(
        text("""
            SELECT *
            FROM t_wordgame_single_game
            WHERE user_id = :user_id
              AND status = 'active'
            ORDER BY started_at DESC
            LIMIT 1
        """),
        {"user_id": user_id}
    ).mappings().first()


def get_user_latest_single_game(db: Session, user_id: int):
    return db.execute(
        text("""
            SELECT *
            FROM t_wordgame_single_game
            WHERE user_id = :user_id
            ORDER BY
                CASE WHEN status = 'active' THEN 0 ELSE 1 END,
                COALESCE(finished_at, started_at) DESC
            LIMIT 1
        """),
        {"user_id": user_id}
    ).mappings().first()


def create_single_game(db: Session, user_id: int):
    db.execute(
        text("""
            INSERT INTO t_wordgame_single_game (
                user_id,
                status,
                total_cells,
                current_position,
                available_rolls,
                today_roll_gained,
                total_roll_gained,
                roll_count_date,
                started_at,
                last_played_at,
                finished_at,
                pending_reward_points,
                claimed_reward_keys,
                reward_log_json
            ) VALUES (
                :user_id,
                'active',
                :total_cells,
                0,
                0,
                0,
                0,
                NULL,
                NOW(),
                NOW(),
                NULL,
                0,
                '[]',
                '[]'
            )
        """),
        {
            "user_id": user_id,
            "total_cells": SINGLE_TOTAL_CELLS,
        }
    )

    return get_user_active_single_game(db, user_id)


def _get_single_claimed_map(db: Session, single_game_id: int):
    rows = db.execute(
        text("""
            SELECT reward_key, points, title, target_day, target_cell, created_at
            FROM t_wordgame_single_reward_claim
            WHERE single_game_id = :single_game_id
        """),
        {"single_game_id": single_game_id}
    ).mappings().all()
    return {r["reward_key"]: dict(r) for r in rows}


def _single_reward_rules_with_status(single_game_id: int, started_at, current_position: int, claimed_map: dict):
    current_day = _single_game_day(started_at)
    position_number = (current_position or 0) + 1
    payload = []
    for rule in SINGLE_REWARD_RULES:
        reward_key = rule["key"]
        claim = claimed_map.get(reward_key)
        unlocked = current_day >= rule["target_day"] and position_number >= rule["target_cell"]
        payload.append({
            "key": reward_key,
            "title": rule["title"],
            "target_day": rule["target_day"],
            "target_cell": rule["target_cell"],
            "points": rule["points"],
            "claimed": claim is not None,
            "unlocked": unlocked,
            "claimed_at": claim.get("created_at") if claim else None,
        })

    finish_claim = claimed_map.get(SINGLE_FINISH_REWARD["key"])
    payload.append({
        "key": SINGLE_FINISH_REWARD["key"],
        "title": SINGLE_FINISH_REWARD["title"],
        "target_day": None,
        "target_cell": SINGLE_TOTAL_CELLS,
        "points": SINGLE_FINISH_REWARD["points"],
        "claimed": finish_claim is not None,
        "unlocked": False,
        "claimed_at": finish_claim.get("created_at") if finish_claim else None,
    })
    return payload


def get_single_game_detail(db: Session, game_id: int):
    row = db.execute(
        text("""
            SELECT *
            FROM t_wordgame_single_game
            WHERE id = :game_id
            LIMIT 1
        """),
        {"game_id": game_id}
    ).mappings().first()

    if not row:
        return None

    claimed_reward_keys = _safe_json_loads(row.get("claimed_reward_keys"), [])
    reward_log = _safe_json_loads(row.get("reward_log_json"), [])
    today_roll_gained = row.get("today_roll_gained", 0) or 0
    try:
        if row.get("roll_count_date") != datetime.now().date():
            today_roll_gained = 0
    except Exception:
        pass

    claimed_map = _get_single_claimed_map(db, row["id"])

    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "status": row["status"],
        "total_cells": row["total_cells"],
        "current_position": row["current_position"],
        "available_rolls": row["available_rolls"],
        "today_roll_gained": today_roll_gained,
        "total_roll_gained": row.get("total_roll_gained", 0) or 0,
        "current_day": _single_game_day(row.get("started_at")),
        "started_at": row.get("started_at"),
        "last_played_at": row.get("last_played_at"),
        "finished_at": row.get("finished_at"),
        "pending_reward_points": row.get("pending_reward_points", 0) or 0,
        "claimed_reward_keys": claimed_reward_keys,
        "reward_log": reward_log,
        "reward_rules": _single_reward_rules_with_status(
            row["id"],
            row.get("started_at"),
            row.get("current_position", 0) or 0,
            claimed_map,
        ),
        "user_points": _get_user_points(db, row["user_id"]),
    }


def _claim_single_reward_if_needed(db: Session, game_row, reward_item: dict):
    existed = db.execute(
        text("""
            SELECT id
            FROM t_wordgame_single_reward_claim
            WHERE single_game_id = :single_game_id
              AND reward_key = :reward_key
            LIMIT 1
        """),
        {
            "single_game_id": game_row["id"],
            "reward_key": reward_item["key"],
        }
    ).mappings().first()

    if existed:
        return None

    db.execute(
        text("""
            INSERT INTO t_wordgame_single_reward_claim (
                user_id,
                single_game_id,
                reward_key,
                title,
                points,
                target_day,
                target_cell,
                created_at
            ) VALUES (
                :user_id,
                :single_game_id,
                :reward_key,
                :title,
                :points,
                :target_day,
                :target_cell,
                NOW()
            )
        """),
        {
            "user_id": game_row["user_id"],
            "single_game_id": game_row["id"],
            "reward_key": reward_item["key"],
            "title": reward_item["title"],
            "points": reward_item["points"],
            "target_day": reward_item.get("target_day"),
            "target_cell": reward_item.get("target_cell"),
        }
    )
    _add_user_points(db, game_row["user_id"], reward_item["points"])

    return {
        **reward_item,
        "claimed_at": _now_text(),
    }


def _grant_single_rewards_if_needed(db: Session, game_row, position_number: int, current_day: int, finished: bool):
    new_rewards = []
    for rule in SINGLE_REWARD_RULES:
        if current_day >= rule["target_day"] and position_number >= rule["target_cell"]:
            reward = _claim_single_reward_if_needed(db, game_row, {
                "key": rule["key"],
                "title": rule["title"],
                "points": rule["points"],
                "target_day": rule["target_day"],
                "target_cell": rule["target_cell"],
            })
            if reward:
                new_rewards.append(reward)

    if finished:
        reward = _claim_single_reward_if_needed(db, game_row, {
            "key": SINGLE_FINISH_REWARD["key"],
            "title": SINGLE_FINISH_REWARD["title"],
            "points": SINGLE_FINISH_REWARD["points"],
            "target_day": None,
            "target_cell": position_number,
        })
        if reward:
            new_rewards.append(reward)

    return new_rewards


def _append_reward_log(existing_row, new_rewards):
    reward_log = _safe_json_loads(existing_row.get("reward_log_json"), [])
    reward_log.extend(new_rewards)
    claimed_keys = set(_safe_json_loads(existing_row.get("claimed_reward_keys"), []))
    for item in new_rewards:
        claimed_keys.add(item["key"])
    return list(claimed_keys), reward_log


# =========================================================
# Multiplayer endpoints
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

    row = _random_question_row(db)
    if not row:
        raise HTTPException(status_code=404, detail="no question found")

    return {
        "word_id": row["word_id"],
        "subcategory_id": row["subcategory_id"],
        "question": row["explanation"],
        "answer": row["english"],
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
        "message": "roll earned",
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

    team_reward = None
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

        reward_rows = _grant_multi_rewards_if_needed(db, existing["match_id"], existing["team"])
        for item in reward_rows:
            if item["user_id"] == user_id:
                team_reward = item
                break

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
        "winner_team": updated["winner_team"],
        "my_reward": team_reward,
        "reward_rules": {
            "win_points": MULTI_WIN_REWARD,
            "lose_points": MULTI_LOSE_REWARD,
        }
    }


# =========================================================
# Single-player endpoints
# =========================================================
@router.post("/single/start")
def start_single_game(user_id: int, db: Session = Depends(get_db)):
    try:
        existing = get_user_active_single_game(db, user_id)
        if existing:
            return {
                "message": "already started",
                "game": get_single_game_detail(db, existing["id"])
            }

        game = create_single_game(db, user_id)
        db.commit()

        return {
            "message": "single game started",
            "game": get_single_game_detail(db, game["id"])
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/single/status")
def get_single_status(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_single_game(db, user_id)
    if existing:
        return {
            "in_single_game": True,
            "game": get_single_game_detail(db, existing["id"]),
            "last_game": None,
            "reward_rules": [
                {
                    "key": rule["key"],
                    "title": rule["title"],
                    "target_day": rule["target_day"],
                    "target_cell": rule["target_cell"],
                    "points": rule["points"],
                }
                for rule in SINGLE_REWARD_RULES
            ],
            "finish_reward": SINGLE_FINISH_REWARD,
        }

    latest = get_user_latest_single_game(db, user_id)
    if latest and latest["status"] == "finished":
        return {
            "in_single_game": False,
            "game": None,
            "last_game": get_single_game_detail(db, latest["id"]),
            "reward_rules": [
                {
                    "key": rule["key"],
                    "title": rule["title"],
                    "target_day": rule["target_day"],
                    "target_cell": rule["target_cell"],
                    "points": rule["points"],
                }
                for rule in SINGLE_REWARD_RULES
            ],
            "finish_reward": SINGLE_FINISH_REWARD,
        }

    return {
        "in_single_game": False,
        "game": None,
        "last_game": None,
        "reward_rules": [
            {
                "key": rule["key"],
                "title": rule["title"],
                "target_day": rule["target_day"],
                "target_cell": rule["target_cell"],
                "points": rule["points"],
            }
            for rule in SINGLE_REWARD_RULES
        ],
        "finish_reward": SINGLE_FINISH_REWARD,
    }


@router.get("/single/quiz-question")
def get_single_quiz_question(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_single_game(db, user_id)
    if not existing:
        raise HTTPException(status_code=400, detail="single game not started")

    row = _random_question_row(db)
    if not row:
        raise HTTPException(status_code=404, detail="no question found")

    return {
        "word_id": row["word_id"],
        "subcategory_id": row["subcategory_id"],
        "question": row["explanation"],
        "answer": row["english"],
        "message": "question loaded"
    }


@router.post("/single/gain-roll")
def single_gain_roll(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_single_game(db, user_id)
    if not existing:
        raise HTTPException(status_code=400, detail="single game not started")

    today = datetime.now().date()
    if existing.get("roll_count_date") != today:
        db.execute(
            text("""
                UPDATE t_wordgame_single_game
                SET today_roll_gained = 0,
                    roll_count_date = CURDATE()
                WHERE id = :game_id
            """),
            {"game_id": existing["id"]}
        )
        current_today_count = 0
    else:
        current_today_count = existing.get("today_roll_gained", 0) or 0

    if current_today_count >= SINGLE_DAILY_GAIN_LIMIT:
        db.rollback()
        raise HTTPException(status_code=400, detail="daily roll gain limit reached (max 3)")

    db.execute(
        text("""
            UPDATE t_wordgame_single_game
            SET today_roll_gained = today_roll_gained + 1,
                total_roll_gained = total_roll_gained + 1,
                available_rolls = available_rolls + 1,
                roll_count_date = CURDATE(),
                last_played_at = NOW()
            WHERE id = :game_id
        """),
        {"game_id": existing["id"]}
    )
    db.commit()

    updated = get_single_game_detail(db, existing["id"])
    remaining = max(0, SINGLE_DAILY_GAIN_LIMIT - updated["today_roll_gained"])

    return {
        "message": "single roll earned",
        "available_rolls": updated["available_rolls"],
        "today_roll_gained": updated["today_roll_gained"],
        "remaining_gain_times_today": remaining
    }


@router.post("/single/roll")
def single_roll(user_id: int, db: Session = Depends(get_db)):
    existing = get_user_active_single_game(db, user_id)
    if not existing:
        raise HTTPException(status_code=400, detail="single game not started")

    if (existing.get("available_rolls", 0) or 0) <= 0:
        raise HTTPException(status_code=400, detail="no rolls")

    step = random.randint(1, 6)
    total_cells = existing.get("total_cells", SINGLE_TOTAL_CELLS) or SINGLE_TOTAL_CELLS
    new_pos = (existing.get("current_position", 0) or 0) + step
    finished = new_pos >= (total_cells - 1)
    if finished:
        new_pos = total_cells - 1

    current_day = _single_game_day(existing.get("started_at"))
    position_number = new_pos + 1

    new_rewards = _grant_single_rewards_if_needed(db, existing, position_number, current_day, finished)
    gained_points = sum(item.get("points", 0) or 0 for item in new_rewards)
    new_pending_points = (existing.get("pending_reward_points", 0) or 0) + gained_points
    claimed_keys, reward_log = _append_reward_log(existing, new_rewards)

    db.execute(
        text("""
            UPDATE t_wordgame_single_game
            SET available_rolls = available_rolls - 1,
                current_position = :new_pos,
                status = CASE WHEN :finished = 1 THEN 'finished' ELSE status END,
                finished_at = CASE WHEN :finished = 1 THEN NOW() ELSE finished_at END,
                last_played_at = NOW(),
                pending_reward_points = :pending_reward_points,
                claimed_reward_keys = :claimed_reward_keys,
                reward_log_json = :reward_log_json
            WHERE id = :game_id
        """),
        {
            "new_pos": new_pos,
            "finished": 1 if finished else 0,
            "pending_reward_points": new_pending_points,
            "claimed_reward_keys": json.dumps(claimed_keys, ensure_ascii=False),
            "reward_log_json": json.dumps(reward_log, ensure_ascii=False),
            "game_id": existing["id"],
        }
    )
    db.commit()

    updated = get_single_game_detail(db, existing["id"])

    return {
        "step": step,
        "status": updated["status"],
        "current_position": updated["current_position"],
        "available_rolls": updated["available_rolls"],
        "current_day": updated["current_day"],
        "new_rewards": new_rewards,
        "pending_reward_points": updated["pending_reward_points"],
        "user_points": updated["user_points"],
        "reward_rules": updated["reward_rules"],
    }
