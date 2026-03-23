# Meta-Learning Problem Generator

An AI-powered system that generates competitive programming and math problems,
learns from your feedback, and continuously adapts difficulty to your skill level.

---

## How It Works

```
LLaMA (local LLM)
       ↓
Problem Generator
       ↓
Automatic Validator (runs solution, checks test cases)
       ↓
You solve the problem
       ↓
Feedback collection (difficulty, clarity, interest)
       ↓
ELO-style skill update
       ↓
Meta-learning: generator improves over time
```

---

## Installation

### Step 1 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 2 — Install Ollama (runs LLaMA locally)

**Mac / Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download the installer from https://ollama.com/download

### Step 3 — Download a model

For math and competitive programming problems, DeepSeek Coder is recommended:

```bash
ollama pull deepseek-coder
```

Or use LLaMA 3 (more general):
```bash
ollama pull llama3
```

### Step 4 — Start Ollama

```bash
ollama serve
```

Leave this running in a separate terminal. Ollama auto-starts on most systems after install.

---

## Running the Agent

### CLI mode (recommended for first run)

```bash
python main.py
```

### Web UI mode

```bash
python web/app.py
```

Then open http://localhost:5000 in your browser.

---

## Configuration

Edit `config.py` to change:
- Model (deepseek-coder, llama3, codellama, etc.)
- Starting difficulty
- Topics (number theory, DP, graphs, combinatorics, etc.)
- Target solve rate (default 60%)

---

## Project Structure

```
meta-problem-generator/
├── main.py                     # CLI entry point
├── config.py                   # Settings
├── requirements.txt
├── generator/
│   ├── problem_generator.py    # LLM problem generation
│   └── validator.py            # Auto-validates solutions
├── meta_learning/
│   ├── difficulty_model.py     # ELO skill tracking
│   └── topic_weights.py        # Learns your weak/strong topics
├── feedback/
│   └── feedback_store.py       # Stores all sessions
├── judge/
│   └── code_runner.py          # Sandboxed code execution
├── web/
│   └── app.py                  # Flask web interface
└── data/                       # Auto-created: feedback, skill history
```

---

## Tech Stack

| Layer        | Tool                        |
|--------------|-----------------------------|
| LLM          | LLaMA / DeepSeek via Ollama |
| Backend      | Python + Flask              |
| Code judge   | subprocess sandbox          |
| Skill model  | ELO rating system           |
| Storage      | JSON (no database needed)   |

---

## Publishing to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/meta-problem-generator.git
git push -u origin main
```
