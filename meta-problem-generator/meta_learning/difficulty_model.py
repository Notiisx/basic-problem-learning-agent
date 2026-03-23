"""
difficulty_model.py
ELO-style student skill tracking.

The core idea: model the probability that a student of skill S solves
a problem of difficulty D, then update both after each attempt.

    P(solve) = 1 / (1 + 10^((D - S) / 400))

This is identical to chess ELO. We want P(solve) ≈ 0.60 (TARGET_SOLVE_RATE),
which keeps problems in the student's optimal learning zone.
"""

import json
import math
import os
from datetime import datetime

from config import (
    STARTING_SKILL,
    STARTING_DIFFICULTY,
    ELO_K_FACTOR,
    TARGET_SOLVE_RATE,
    SKILL_FILE,
    DATA_DIR,
)


def _load_skill_history() -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(SKILL_FILE):
        with open(SKILL_FILE) as f:
            return json.load(f)
    return [{"skill": STARTING_SKILL, "timestamp": datetime.now().isoformat()}]


def _save_skill_history(history: list) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(SKILL_FILE, "w") as f:
        json.dump(history, f, indent=2)


def get_current_skill() -> float:
    history = _load_skill_history()
    return history[-1]["skill"]


def solve_probability(student_skill: float, problem_difficulty: float) -> float:
    """Expected probability that this student solves this problem."""
    return 1.0 / (1.0 + 10 ** ((problem_difficulty - student_skill) / 400))


def update_skill(solved: bool, problem_difficulty: float) -> dict:
    """
    Update student ELO based on solve outcome.
    Returns dict with old_skill, new_skill, delta.
    """
    history = _load_skill_history()
    old_skill = history[-1]["skill"]

    expected = solve_probability(old_skill, problem_difficulty)
    actual   = 1.0 if solved else 0.0

    delta = ELO_K_FACTOR * (actual - expected)
    new_skill = round(old_skill + delta, 1)

    history.append({
        "skill":      new_skill,
        "delta":      round(delta, 1),
        "solved":     solved,
        "difficulty": problem_difficulty,
        "timestamp":  datetime.now().isoformat(),
    })
    _save_skill_history(history)

    return {"old_skill": old_skill, "new_skill": new_skill, "delta": round(delta, 1)}


def recommend_difficulty(student_skill: float) -> float:
    """
    Return a difficulty value that gives ~TARGET_SOLVE_RATE probability.

    Solve for D given P = TARGET_SOLVE_RATE:
        D = S - 400 * log10(1/P - 1)
    """
    p = TARGET_SOLVE_RATE
    difficulty = student_skill - 400 * math.log10(1 / p - 1)
    return round(difficulty)
