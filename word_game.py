import random
from dataclasses import asdict, dataclass, field
from threading import Lock

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


@dataclass
class TeamState:
    name: str
    color: str
    token_label: str
    position: int = 0
    dice_pool: int = 0
    member_study_counts: list = field(default_factory=lambda: [0, 0])

    def remaining_study_chances(self, member_index: int) -> int:
        return max(0, 3 - self.member_study_counts[member_index])

    def total_remaining_study_chances(self) -> int:
        return sum(max(0, 3 - c) for c in self.member_study_counts)


class WordRaceGame:
    def __init__(self, total_cells: int = 84):
        self.total_cells = total_cells
        self.reset_match()

    def reset_match(self):
        self.red_team = TeamState(name="Red Team", color="#ef4444", token_label="R")
        self.blue_team = TeamState(name="Blue Team", color="#3b82f6", token_label="B")
        self.active_team_name = self.red_team.name
        self.winner_name = None
        self.current_day = 1

    def get_active_team(self) -> TeamState:
        return self.red_team if self.active_team_name == self.red_team.name else self.blue_team

    def switch_team(self):
        if self.winner_name:
            return
        self.active_team_name = (
            self.blue_team.name if self.active_team_name == self.red_team.name else self.red_team.name
        )

    def study_for_member(self, member_index: int):
        if self.winner_name:
            return False, "Match already finished."

        if member_index not in (0, 1):
            return False, "member_index must be 0 or 1."

        team = self.get_active_team()
        if team.remaining_study_chances(member_index) <= 0:
            return False, f"{team.name} - Member {member_index + 1} has no study chances left today."

        team.member_study_counts[member_index] += 1
        team.dice_pool += 1
        return True, f"{team.name} - Member {member_index + 1} answered correctly. +1 shared dice gained."

    def roll_dice(self):
        if self.winner_name:
            return False, "Match already finished.", None

        team = self.get_active_team()
        if team.dice_pool <= 0:
            return False, f"{team.name} has no dice left.", None

        roll = random.randint(1, 6)
        team.dice_pool -= 1
        team.position += roll

        if team.position >= self.total_cells - 1:
            team.position = self.total_cells - 1
            self.winner_name = team.name
            return True, f"{team.name} rolled {roll} and reached the goal first!", roll

        return True, f"{team.name} rolled a {roll}. Current position: cell {team.position + 1}", roll

    def advance_to_next_day(self):
        self.current_day += 1
        self.red_team.member_study_counts = [0, 0]
        self.blue_team.member_study_counts = [0, 0]
        return f"It is now Day {self.current_day}. All members can study up to 3 times again today."

    def state_dict(self):
        return {
            "total_cells": self.total_cells,
            "current_day": self.current_day,
            "active_team_name": self.active_team_name,
            "winner_name": self.winner_name,
            "red_team": asdict(self.red_team),
            "blue_team": asdict(self.blue_team),
        }


class StudyRequest(BaseModel):
    member_index: int


app = FastAPI(title="Word Race API")

game = WordRaceGame(total_cells=84)
game_lock = Lock()


@app.get("/")
def root():
    return {"message": "Word Race FastAPI backend is running."}


@app.get("/game/state")
def get_game_state():
    with game_lock:
        return game.state_dict()


@app.post("/game/switch-team")
def switch_team():
    with game_lock:
        game.switch_team()
        return {
            "message": f"Now controlling {game.active_team_name}.",
            "state": game.state_dict(),
        }


@app.post("/game/study")
def study(req: StudyRequest):
    with game_lock:
        ok, message = game.study_for_member(req.member_index)
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        return {
            "message": message,
            "state": game.state_dict(),
        }


@app.post("/game/roll")
def roll_dice():
    with game_lock:
        ok, message, roll = game.roll_dice()
        if not ok:
            raise HTTPException(status_code=400, detail=message)
        return {
            "message": message,
            "roll": roll,
            "state": game.state_dict(),
        }


@app.post("/game/next-day")
def next_day():
    with game_lock:
        message = game.advance_to_next_day()
        return {
            "message": message,
            "state": game.state_dict(),
        }


@app.post("/game/reset")
def reset_game():
    with game_lock:
        game.reset_match()
        return {
            "message": "Match reset successfully.",
            "state": game.state_dict(),
        }