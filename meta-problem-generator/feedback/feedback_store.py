"""
feedback_store.py
Persists all session data: problems seen, feedback scores, solve outcomes.
Used by the meta-learning loop to improve generation over time.
"""

import json
import os
from datetime import datetime
from config import FEEDBACK_FILE, DATA_DIR


def _load() -> list:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(FEEDBACK_FILE):
        with open(FEEDBACK_FILE) as f:
            return json.load(f)
    return []


def store_session(
    topic: str,
    difficulty: int,
    solved: bool,
    solve_time_seconds: float,
    difficulty_rating: int,   # 1–5
    clarity_rating: int,      # 1–5
    interest_rating: int,     # 1–5
    hint_used: bool = False,
) -> None:
    """Append one problem session to the feedback log."""
    sessions = _load()
    sessions.append({
        "timestamp":         datetime.now().isoformat(),
        "topic":             topic,
        "difficulty":        difficulty,
        "solved":            solved,
        "solve_time":        round(solve_time_seconds, 1),
        "difficulty_rating": difficulty_rating,
        "clarity_rating":    clarity_rating,
        "interest_rating":   interest_rating,
        "hint_used":         hint_used,
    })
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FEEDBACK_FILE, "w") as f:
        json.dump(sessions, f, indent=2)


def get_summary() -> dict:
    """Return aggregate stats across all sessions."""
    sessions = _load()
    if not sessions:
        return {"total": 0}

    total   = len(sessions)
    solved  = sum(1 for s in sessions if s["solved"])
    by_topic: dict = {}

    for s in sessions:
        t = s["topic"]
        if t not in by_topic:
            by_topic[t] = {"attempts": 0, "solved": 0}
        by_topic[t]["attempts"] += 1
        if s["solved"]:
            by_topic[t]["solved"] += 1

    return {
        "total":        total,
        "solved":       solved,
        "solve_rate":   round(solved / total, 2),
        "by_topic":     by_topic,
    }


def get_all_sessions() -> list:
    return _load()
