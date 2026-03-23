# ─────────────────────────────────────────────
#  config.py  –  all tuneable settings in one place
# ─────────────────────────────────────────────

# Ollama endpoint (leave as-is if running locally)
OLLAMA_URL = "http://localhost:11434/api/generate"

# Model to use.
# Recommended options (pull with: ollama pull <name>):
#   deepseek-coder   ← best for programming problems
#   llama3           ← best for math / number theory
#   codellama        ← alternative coding model
MODEL = "deepseek-coder"

# ── Difficulty / ELO ──────────────────────────
STARTING_SKILL      = 1200   # ELO starting point
STARTING_DIFFICULTY = 1200
ELO_K_FACTOR        = 20     # how fast skill updates
TARGET_SOLVE_RATE   = 0.60   # aim for 60% success rate

# ── Topics & weights ─────────────────────────
# Weights control how often each topic is chosen.
# The meta-learner adjusts these based on your feedback.
TOPIC_WEIGHTS = {
    "number theory":    1.0,
    "combinatorics":    1.0,
    "dynamic programming": 1.0,
    "graph theory":     1.0,
    "binary search":    1.0,
    "greedy":           1.0,
    "modular arithmetic": 1.0,
}

# ── Validation ────────────────────────────────
MAX_VALIDATION_ATTEMPTS = 3   # retries before discarding a problem
CODE_TIMEOUT_SECONDS    = 5   # sandbox execution limit

# ── Storage ───────────────────────────────────
DATA_DIR         = "data"
FEEDBACK_FILE    = "data/feedback.json"
SKILL_FILE       = "data/skill_history.json"
TOPIC_FILE       = "data/topic_weights.json"
