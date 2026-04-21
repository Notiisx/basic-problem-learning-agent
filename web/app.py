"""
web/app.py  –  Flask web interface for the meta-learning problem generator.

Usage (from project root):
    python web/app.py
Then open http://localhost:5000

FIXES applied vs original:
  - Serves templates/index.html instead of duplicated inline HTML
  - Added missing /generate, /submit, /feedback, /stats routes
    (templates/index.html uses these without /api/ prefix)
  - /generate now honours forced topic from the form
  - /submit endpoint added for code judging (was completely absent)
  - /feedback uses FormData (matches what the template POSTs)
  - /feedback returns clarity_warning and full fields expected by template
  - /generate returns student_skill, solve_probability, title fields
  - Session state stored per Flask session (not bare module-level global)
  - Topic keys are underscore-based throughout (matches config.py)
"""

import sys
import os
import time

# Allow running from web/ subdirectory OR from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, render_template, session

from generator.problem_generator import generate_problem
from generator.validator import validate_problem
from judge.code_runner import judge_against_test_cases
from meta_learning.difficulty_model import (
    get_current_skill,
    update_skill,
    recommend_difficulty,
    solve_probability,
    get_skill_history,
)
from meta_learning.topic_weights import choose_topic, update_weights, get_topic_stats
from feedback.feedback_store import store_session, get_summary, get_recent_solve_rate
from config import MAX_VALIDATION_ATTEMPTS, TOPIC_LABELS, MODEL

app = Flask(
    __name__,
    # FIX: serve from the project-level templates/ folder regardless of cwd
    template_folder=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "templates",
    ),
)

# Required for flask.session
app.secret_key = os.environ.get("SECRET_KEY", "meta-learn-dev-key-change-in-prod")

# ── In-memory problem state per server process ────────────────────────────────
# FIX: use Flask session to scope per browser session instead of a bare global
# For simplicity on a single-user local tool we keep a dict keyed by session id.
_sessions: dict = {}


def _get_state() -> dict:
    sid = session.get("sid")
    if sid and sid in _sessions:
        return _sessions[sid]
    return {}


def _set_state(data: dict) -> None:
    import uuid
    sid = session.get("sid")
    if not sid:
        sid = str(uuid.uuid4())
        session["sid"] = sid
    _sessions[sid] = data


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    # FIX: use the proper templates/index.html (was using inline HTML string)
    return render_template("index.html")


# ── API routes (called by templates/index.html JS) ────────────────────────────

@app.route("/stats")
def stats():
    """
    FIX: route was /api/stats in old code, but templates/index.html calls /stats.
    Returns stats + topic weights for the sidebar.
    """
    skill   = get_current_skill()
    summary = get_summary()
    weights = get_topic_stats()

    # Attach human-readable labels
    labeled_weights = {
        TOPIC_LABELS.get(k, k): v for k, v in weights.items()
    }

    return jsonify({
        "total_attempts":    summary.get("total", 0),
        "solved":            summary.get("solved", 0),
        "recent_solve_rate": get_recent_solve_rate(10),
        "student_skill":     skill,
        "topic_weights":     labeled_weights,
        "raw_topic_weights": weights,
        "skill_history":     get_skill_history()[-20:],
        "model":             MODEL,
    })


@app.route("/generate", methods=["POST"])
def generate():
    """
    FIX: was /api/generate; templates/index.html calls /generate.
    FIX: now honours forced topic from form data.
    FIX: returns all fields that templates/index.html expects:
         student_skill, solve_probability, difficulty, topic, title,
         statement, input_format, output_format, constraints.
    """
    skill = get_current_skill()

    # FIX: read forced topic from FormData (empty = weighted random)
    forced_topic = (request.form.get("topic") or "").strip()
    topic        = choose_topic(forced=forced_topic)
    difficulty   = recommend_difficulty(skill)
    p_solve      = solve_probability(skill, difficulty)

    problem = None
    last_error = "Could not generate a valid problem."

    for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
        try:
            candidate = generate_problem(topic, difficulty)
        except (RuntimeError, ValueError) as e:
            last_error = str(e)
            if "Cannot reach Ollama" in last_error:
                return jsonify({"error": last_error}), 503
            continue

        ok, reason = validate_problem(candidate)
        if ok:
            problem = candidate
            break
        last_error = reason

    if problem is None:
        return jsonify({"error": last_error}), 422

    # Store in per-session state
    _set_state({
        "problem":    problem,
        "topic":      topic,
        "difficulty": difficulty,
        "start_time": time.time(),
    })

    display_topic = TOPIC_LABELS.get(topic, topic.replace("_", " ").title())

    return jsonify({
        "topic":             display_topic,
        "raw_topic":         topic,
        "difficulty":        difficulty,
        "student_skill":     skill,
        "solve_probability": round(p_solve, 3),
        "title":             problem.get("title") or f"{display_topic} — ELO {difficulty}",
        "statement":         problem.get("statement", ""),
        "input_format":      problem.get("input_format", ""),
        "output_format":     problem.get("output_format", ""),
        "note":              problem.get("note", ""),
        "examples":          problem.get("test_cases", [])[:2],
    })


@app.route("/submit", methods=["POST"])
def submit():
    """
    FIX: this route was COMPLETELY MISSING from the original app.py.
    templates/index.html calls /submit to judge student code.

    Accepts: FormData with field 'code'
    Returns: verdict, passed, total, details
    """
    state = _get_state()
    if not state or not state.get("problem"):
        return jsonify({"error": "No active problem. Generate one first."}), 400

    code = (request.form.get("code") or "").strip()
    if not code:
        return jsonify({"error": "No code submitted."}), 400

    problem    = state["problem"]
    test_cases = problem.get("test_cases", [])

    result = judge_against_test_cases(code, test_cases)
    return jsonify(result)


@app.route("/feedback", methods=["POST"])
def feedback():
    """
    FIX: was /api/feedback; templates/index.html calls /feedback.
    FIX: reads FormData (not JSON) — templates/index.html uses FormData.
    FIX: returns all fields templates/index.html expects:
         skill_before, skill_after, next_difficulty, topic_weights,
         clarity_warning.
    """
    state = _get_state()
    if not state or not state.get("problem"):
        return jsonify({"error": "No active problem."}), 400

    # FIX: read from FormData (templates/index.html uses FormData, not JSON)
    solved           = request.form.get("solved", "false").lower() == "true"
    difficulty_rating = int(request.form.get("difficulty_rating", 3))
    clarity_rating    = int(request.form.get("clarity_rating",    3))
    interest_rating   = int(request.form.get("interest_rating",   3))

    elapsed    = time.time() - (state.get("start_time") or time.time())
    topic      = state["topic"]
    difficulty = state["difficulty"]

    skill_update = update_skill(solved, difficulty)
    update_weights(topic, solved, interest_rating)
    store_session(
        topic              = topic,
        difficulty         = difficulty,
        solved             = solved,
        solve_time_seconds = elapsed,
        difficulty_rating  = difficulty_rating,
        clarity_rating     = clarity_rating,
        interest_rating    = interest_rating,
    )

    new_skill     = skill_update["new_skill"]
    next_diff     = recommend_difficulty(new_skill)
    weights       = get_topic_stats()
    clarity_warning = clarity_rating <= 2
    labeled_weights = {TOPIC_LABELS.get(k, k): v for k, v in weights.items()}

    return jsonify({
        "skill_before":    skill_update["old_skill"],
        "skill_after":     new_skill,
        "delta":           skill_update["delta"],
        "next_difficulty": next_diff,
        "topic_weights":   labeled_weights,
        "clarity_warning": clarity_warning,
    })


# ── Keep /api/* aliases so the simpler web UI also works ─────────────────────

@app.route("/api/stats")
def api_stats():
    return stats()


@app.route("/api/generate", methods=["POST"])
def api_generate():
    return generate()


@app.route("/api/hint")
def api_hint():
    state = _get_state()
    if not state or not state.get("problem"):
        return jsonify({"hint": "No active problem."})
    return jsonify({"hint": state["problem"]["solution_explanation"]})


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    """Alias that accepts JSON (for the simpler inline-HTML UI)."""
    state = _get_state()
    if not state or not state.get("problem"):
        return jsonify({"error": "No active problem."}), 400

    data             = request.get_json(force=True) or {}
    solved           = data.get("solved", False)
    difficulty_rating = int(data.get("difficulty_rating", 3))
    clarity_rating    = int(data.get("clarity_rating",    3))
    interest_rating   = int(data.get("interest_rating",   3))

    elapsed    = time.time() - (state.get("start_time") or time.time())
    topic      = state["topic"]
    difficulty = state["difficulty"]

    skill_update = update_skill(solved, difficulty)
    update_weights(topic, solved, interest_rating)
    store_session(
        topic              = topic,
        difficulty         = difficulty,
        solved             = solved,
        solve_time_seconds = elapsed,
        difficulty_rating  = difficulty_rating,
        clarity_rating     = clarity_rating,
        interest_rating    = interest_rating,
    )

    return jsonify({
        "old_skill":   skill_update["old_skill"],
        "new_skill":   skill_update["new_skill"],
        "skill_delta": skill_update["delta"],
    })


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  Meta-Learning Problem Generator")
    print("  http://localhost:5000")
    print("=" * 55)
    app.run(debug=True, port=5000)
