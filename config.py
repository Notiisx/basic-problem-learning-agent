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
MODEL = "qwen2.5-coder:3b"

# ── Difficulty / ELO ──────────────────────────
STARTING_SKILL      = 800    # ELO starting point
STARTING_DIFFICULTY = 800
ELO_K_FACTOR        = 20     # how fast skill updates
TARGET_SOLVE_RATE   = 0.60   # aim for 60% success rate

# ── Topics & weights ─────────────────────────
# FIX: topic keys now use underscores consistently across all modules.
# Weights control how often each topic is chosen.
# The meta-learner adjusts these based on your feedback.
TOPIC_WEIGHTS = {
    "number_theory":        1.0,
    "combinatorics":        1.0,
    "dynamic_programming":  1.0,
    "graph_theory":         1.0,
    "binary_search":        1.0,
    "greedy":               1.0,
    "modular_arithmetic":   1.0,
}

# Human-readable labels for display
TOPIC_LABELS = {
    "number_theory":        "Number Theory",
    "combinatorics":        "Combinatorics",
    "dynamic_programming":  "Dynamic Programming",
    "graph_theory":         "Graph Theory",
    "binary_search":        "Binary Search",
    "greedy":               "Greedy",
    "modular_arithmetic":   "Modular Arithmetic",
}

# ── Validation ────────────────────────────────
MAX_VALIDATION_ATTEMPTS = 3   # retries before discarding a problem
CODE_TIMEOUT_SECONDS    = 5   # sandbox execution limit

# ── Storage ───────────────────────────────────
DATA_DIR         = "data"
FEEDBACK_FILE    = "data/feedback.json"
SKILL_FILE       = "data/skill_history.json"
TOPIC_FILE       = "data/topic_weights.json"
