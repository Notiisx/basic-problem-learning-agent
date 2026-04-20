"""
topic_weights.py
Tracks per-topic performance and adjusts generation weights.

Logic:
  - If you fail a topic often → increase its weight (you need more practice)
  - If you rate a topic very interesting → slight weight boost
  - If you ace a topic consistently → slight weight decrease (you've mastered it)
"""

import json
import os
import random
from config import TOPIC_WEIGHTS, TOPIC_FILE, DATA_DIR


def _load_weights() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(TOPIC_FILE):
        with open(TOPIC_FILE) as f:
            return json.load(f)
    # FIX: initialize from config (now uses underscore keys)
    return dict(TOPIC_WEIGHTS)


def _save_weights(weights: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(TOPIC_FILE, "w") as f:
        json.dump(weights, f, indent=2)


def get_weights() -> dict:
    return _load_weights()


def choose_topic(forced: str = "") -> str:
    """
    Weighted random topic selection.
    FIX: accepts optional forced topic override (empty string = random).
    """
    weights = _load_weights()

    # FIX: support forced topic from the web UI
    if forced and forced in weights:
        return forced

    topics = list(weights.keys())
    values = list(weights.values())
    return random.choices(topics, weights=values, k=1)[0]


def update_weights(topic: str, solved: bool, interest_score: int) -> None:
    """
    Adjust topic weight after a problem attempt.
      - Failed: +0.15 (need more practice)
      - Solved: -0.05 (slight reduction, still practiced)
      - High interest (≥4): +0.10 bonus
    """
    weights = _load_weights()

    # FIX: ensure topic exists even if it wasn't in original config
    if topic not in weights:
        weights[topic] = 1.0

    delta = -0.05 if solved else 0.15

    if interest_score >= 4:
        delta += 0.10

    # Clamp between 0.1 and 3.0
    weights[topic] = round(max(0.1, min(3.0, weights[topic] + delta)), 2)

    _save_weights(weights)


def get_topic_stats() -> dict:
    """Return current weights for display."""
    return _load_weights()
