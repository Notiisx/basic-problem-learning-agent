"""
web/app.py  –  Flask web interface for the meta-learning problem generator.

Usage:
    python web/app.py
Then open http://localhost:5000
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from flask import Flask, jsonify, request, render_template_string

from generator.problem_generator import generate_problem
from generator.validator import validate_problem
from meta_learning.difficulty_model import (
    get_current_skill, update_skill, recommend_difficulty, solve_probability,
)
from meta_learning.topic_weights import choose_topic, update_weights, get_topic_stats
from feedback.feedback_store import store_session, get_summary
from config import MAX_VALIDATION_ATTEMPTS

app = Flask(__name__)

# Simple in-memory state for the current problem session
_state = {
    "problem":    None,
    "topic":      None,
    "difficulty": None,
    "start_time": None,
}

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Meta Problem Generator</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap');

  :root {
    --bg:     #0d0f14;
    --panel:  #13161e;
    --border: #1e2330;
    --accent: #7c6af7;
    --green:  #4ade80;
    --red:    #f87171;
    --text:   #c9d1e0;
    --muted:  #5a647a;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    min-height: 100vh;
    padding: 2rem;
  }

  h1 {
    font-family: 'Syne', sans-serif;
    font-size: 1.8rem;
    font-weight: 800;
    color: #fff;
    margin-bottom: 0.25rem;
  }

  .subtitle { color: var(--muted); font-size: 0.8rem; margin-bottom: 2rem; }

  .grid {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1.5rem;
    max-width: 1100px;
  }

  .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
  }

  .card-title {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: var(--accent);
    margin-bottom: 1rem;
  }

  .problem-text {
    white-space: pre-wrap;
    line-height: 1.7;
    font-size: 0.88rem;
    color: #e2e8f0;
  }

  .stat { margin-bottom: 0.75rem; }
  .stat-label { color: var(--muted); font-size: 0.75rem; }
  .stat-value { font-size: 1.1rem; font-weight: 700; color: #fff; }

  .elo-bar-wrap { margin-top: 1rem; }
  .elo-bar {
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
    margin-top: 4px;
  }
  .elo-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--accent), #a78bfa);
    border-radius: 3px;
    transition: width 0.6s ease;
  }

  .topic-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.3rem 0;
    font-size: 0.78rem;
    border-bottom: 1px solid var(--border);
  }
  .topic-row:last-child { border: none; }
  .topic-weight {
    font-weight: 700;
    color: var(--accent);
    min-width: 2.5rem;
    text-align: right;
  }

  button {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    font-weight: 700;
    padding: 0.6rem 1.4rem;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    transition: opacity 0.15s;
  }
  button:hover { opacity: 0.85; }
  button:disabled { opacity: 0.4; cursor: default; }

  .btn-primary { background: var(--accent); color: #fff; }
  .btn-success { background: var(--green);  color: #0d0f14; }
  .btn-danger  { background: var(--red);    color: #0d0f14; }
  .btn-ghost   { background: var(--border); color: var(--text); }

  .btn-row { display: flex; gap: 0.75rem; margin-top: 1rem; flex-wrap: wrap; }

  .rating-group { margin: 0.5rem 0; }
  .rating-group label { font-size: 0.8rem; color: var(--muted); display: block; margin-bottom: 0.25rem; }
  .stars { display: flex; gap: 0.4rem; }
  .star {
    width: 28px; height: 28px;
    background: var(--border);
    border-radius: 4px;
    display: flex; align-items: center; justify-content: center;
    cursor: pointer;
    font-size: 0.85rem;
    transition: background 0.1s;
  }
  .star.active { background: var(--accent); color: #fff; }

  .hint-box {
    background: #0a0d13;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem;
    margin-top: 1rem;
    white-space: pre-wrap;
    font-size: 0.82rem;
    color: #94a3b8;
    display: none;
  }

  .status-msg {
    font-size: 0.82rem;
    padding: 0.5rem 0;
    min-height: 1.5rem;
    color: var(--muted);
  }

  .spinner {
    display: inline-block;
    width: 14px; height: 14px;
    border: 2px solid var(--muted);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    vertical-align: middle;
    margin-right: 6px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 700px) {
    .grid { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>

<h1>Meta Problem Generator</h1>
<p class="subtitle">adaptive difficulty · local LLM · ELO skill tracking</p>

<div class="grid">

  <!-- Left: Problem Panel -->
  <div>
    <div class="card">
      <div class="card-title" id="problem-topic">Press "New Problem" to begin</div>
      <div class="problem-text" id="problem-text" style="color:var(--muted)">
Your problem will appear here. The system will generate and validate it using
your local LLaMA model before showing it to you.
      </div>
      <div class="hint-box" id="hint-box"></div>
    </div>

    <div class="card" style="margin-top:1rem;" id="feedback-card" hidden>
      <div class="card-title">Feedback</div>

      <div class="rating-group">
        <label>Difficulty felt appropriate?</label>
        <div class="stars" id="stars-diff">
          <div class="star" onclick="rate('diff',1)">1</div>
          <div class="star" onclick="rate('diff',2)">2</div>
          <div class="star" onclick="rate('diff',3)">3</div>
          <div class="star" onclick="rate('diff',4)">4</div>
          <div class="star" onclick="rate('diff',5)">5</div>
        </div>
      </div>

      <div class="rating-group">
        <label>Clarity of the problem statement?</label>
        <div class="stars" id="stars-clarity">
          <div class="star" onclick="rate('clarity',1)">1</div>
          <div class="star" onclick="rate('clarity',2)">2</div>
          <div class="star" onclick="rate('clarity',3)">3</div>
          <div class="star" onclick="rate('clarity',4)">4</div>
          <div class="star" onclick="rate('clarity',5)">5</div>
        </div>
      </div>

      <div class="rating-group">
        <label>How interesting was the topic?</label>
        <div class="stars" id="stars-interest">
          <div class="star" onclick="rate('interest',1)">1</div>
          <div class="star" onclick="rate('interest',2)">2</div>
          <div class="star" onclick="rate('interest',3)">3</div>
          <div class="star" onclick="rate('interest',4)">4</div>
          <div class="star" onclick="rate('interest',5)">5</div>
        </div>
      </div>

      <div class="btn-row">
        <button class="btn-success" onclick="submitFeedback(true)">✓ Solved it</button>
        <button class="btn-danger"  onclick="submitFeedback(false)">✗ Didn't solve it</button>
      </div>
    </div>

    <div class="status-msg" id="status"></div>
  </div>

  <!-- Right: Stats Panel -->
  <div>
    <div class="card">
      <div class="card-title">Your Stats</div>
      <div class="stat">
        <div class="stat-label">Skill Rating</div>
        <div class="stat-value" id="skill-val">—</div>
        <div class="elo-bar-wrap">
          <div class="elo-bar"><div class="elo-fill" id="elo-fill" style="width:50%"></div></div>
        </div>
      </div>
      <div class="stat">
        <div class="stat-label">Next problem difficulty</div>
        <div class="stat-value" id="diff-val">—</div>
      </div>
      <div class="stat">
        <div class="stat-label">Solve rate</div>
        <div class="stat-value" id="rate-val">—</div>
      </div>
      <div class="stat">
        <div class="stat-label">Problems attempted</div>
        <div class="stat-value" id="total-val">—</div>
      </div>
    </div>

    <div class="card" style="margin-top:1rem;">
      <div class="card-title">Topic Weights</div>
      <div id="topic-weights"></div>
    </div>

    <div class="btn-row" style="margin-top:1rem;">
      <button class="btn-primary" id="btn-new" onclick="newProblem()">⚡ New Problem</button>
      <button class="btn-ghost"   id="btn-hint" onclick="showHint()" disabled>💡 Hint</button>
    </div>
  </div>

</div>

<script>
  const ratings = { diff: 3, clarity: 3, interest: 3 };

  function rate(key, val) {
    ratings[key] = val;
    const stars = document.querySelectorAll(`#stars-${key} .star`);
    stars.forEach((s, i) => s.classList.toggle('active', i < val));
  }

  // Init stars at 3
  ['diff','clarity','interest'].forEach(k => rate(k, 3));

  function setStatus(msg, spin=false) {
    const el = document.getElementById('status');
    el.innerHTML = spin ? `<span class="spinner"></span>${msg}` : msg;
  }

  async function loadStats() {
    const r = await fetch('/api/stats');
    const d = await r.json();
    document.getElementById('skill-val').textContent = d.skill;
    document.getElementById('diff-val').textContent  = d.recommended_difficulty;
    document.getElementById('rate-val').textContent  =
      d.total > 0 ? (d.solve_rate * 100).toFixed(0) + '%' : '—';
    document.getElementById('total-val').textContent = d.total;

    // ELO bar: map 800–1800 to 0–100%
    const pct = Math.min(100, Math.max(0, (d.skill - 800) / 10));
    document.getElementById('elo-fill').style.width = pct + '%';

    // Topic weights
    const tw = document.getElementById('topic-weights');
    tw.innerHTML = '';
    const sorted = Object.entries(d.topic_weights).sort((a,b) => b[1]-a[1]);
    sorted.forEach(([t, w]) => {
      const row = document.createElement('div');
      row.className = 'topic-row';
      row.innerHTML = `<span>${t}</span><span class="topic-weight">${w.toFixed(2)}</span>`;
      tw.appendChild(row);
    });
  }

  async function newProblem() {
    document.getElementById('btn-new').disabled = true;
    document.getElementById('btn-hint').disabled = true;
    document.getElementById('feedback-card').hidden = true;
    document.getElementById('hint-box').style.display = 'none';
    setStatus('Generating and validating problem…', true);

    const r = await fetch('/api/generate', { method: 'POST' });
    const d = await r.json();

    document.getElementById('btn-new').disabled = false;

    if (d.error) {
      setStatus('Error: ' + d.error);
      return;
    }

    document.getElementById('problem-topic').textContent =
      `${d.topic}  ·  difficulty ${d.difficulty}`;
    document.getElementById('problem-text').textContent =
      d.statement + (d.constraints ? '\n\nConstraints:\n' + d.constraints : '');
    document.getElementById('feedback-card').hidden = false;
    document.getElementById('btn-hint').disabled = false;
    setStatus('');
    loadStats();
  }

  function showHint() {
    const box = document.getElementById('hint-box');
    if (box.style.display === 'none' || !box.style.display) {
      fetch('/api/hint').then(r => r.json()).then(d => {
        box.textContent = d.hint;
        box.style.display = 'block';
      });
    } else {
      box.style.display = 'none';
    }
  }

  async function submitFeedback(solved) {
    setStatus('Saving…', true);
    const body = {
      solved,
      difficulty_rating:  ratings.diff,
      clarity_rating:     ratings.clarity,
      interest_rating:    ratings.interest,
    };
    const r = await fetch('/api/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    document.getElementById('feedback-card').hidden = true;
    const emoji = solved ? '✓' : '✗';
    const delta = d.skill_delta > 0 ? `+${d.skill_delta}` : d.skill_delta;
    setStatus(`${emoji}  Skill: ${d.old_skill} → ${d.new_skill}  (${delta})`);
    loadStats();
  }

  loadStats();
</script>
</body>
</html>
"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/stats")
def stats():
    skill = get_current_skill()
    summary = get_summary()
    return jsonify({
        "skill":                 skill,
        "recommended_difficulty": recommend_difficulty(skill),
        "total":                 summary.get("total", 0),
        "solve_rate":            summary.get("solve_rate", 0),
        "topic_weights":         get_topic_stats(),
    })


@app.route("/api/generate", methods=["POST"])
def api_generate():
    skill      = get_current_skill()
    topic      = choose_topic()
    difficulty = recommend_difficulty(skill)

    problem = None
    for _ in range(MAX_VALIDATION_ATTEMPTS):
        try:
            candidate = generate_problem(topic, difficulty)
        except (RuntimeError, ValueError) as e:
            return jsonify({"error": str(e)})

        ok, reason = validate_problem(candidate)
        if ok:
            problem = candidate
            break

    if problem is None:
        return jsonify({"error": "Could not generate a valid problem. Try again."})

    # Store in app state
    _state["problem"]    = problem
    _state["topic"]      = topic
    _state["difficulty"] = difficulty
    _state["start_time"] = time.time()

    return jsonify({
        "topic":       topic,
        "difficulty":  difficulty,
        "statement":   problem["statement"],
        "constraints": problem["constraints"],
    })


@app.route("/api/hint")
def api_hint():
    if _state["problem"] is None:
        return jsonify({"hint": "No active problem."})
    return jsonify({"hint": _state["problem"]["solution_explanation"]})


@app.route("/api/feedback", methods=["POST"])
def api_feedback():
    data = request.get_json()
    if _state["problem"] is None:
        return jsonify({"error": "No active problem."})

    elapsed = time.time() - (_state["start_time"] or time.time())
    solved  = data.get("solved", False)

    skill_update = update_skill(solved, _state["difficulty"])
    update_weights(_state["topic"], solved, data.get("interest_rating", 3))
    store_session(
        topic              = _state["topic"],
        difficulty         = _state["difficulty"],
        solved             = solved,
        solve_time_seconds = elapsed,
        difficulty_rating  = data.get("difficulty_rating", 3),
        clarity_rating     = data.get("clarity_rating", 3),
        interest_rating    = data.get("interest_rating", 3),
    )

    return jsonify({
        "old_skill":  skill_update["old_skill"],
        "new_skill":  skill_update["new_skill"],
        "skill_delta": skill_update["delta"],
    })


if __name__ == "__main__":
    print("Starting web interface at http://localhost:5000")
    app.run(debug=True, port=5000)
