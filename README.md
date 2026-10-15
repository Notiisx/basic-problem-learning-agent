# Problem Learning Agent for Competitive Programming

An adaptive practice tool that generates competitive-programming problems with a local LLM and tunes itself to the you (the user). After each problem it updates an ELO-style skill rating and per-topic weights, so the next problem is pitched at a ~60% solve rate and leans toward topics you will find useful.

## Features

- **Problem generation:** a local model via [Ollama](https://ollama.com) writes problems with constraints, test cases and a reference solution
- **Validation:** each generated solution is run against its own test cases before you see the problem
- **Judging:** submit Python code and it is checked against the test cases, with a time limit
- **Adaptive difficulty:** your skill rating rises or falls with each attempt, and the next difficulty follows it
- **Topic weighting:** your ratings shift which of the 7 topics come up more often: number theory, combinatorics, dynamic programming, graph theory, binary search, greedy, modular arithmetic
- **Feedback loop:** rate each problem's difficulty, clarity and interest

## Requirements

- Python 3
- [Ollama](https://ollama.com) running locally with the default model:

```bash
ollama pull qwen2.5-coder:3b
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

**Web UI** (Flask, http://localhost:5000):

```bash
python web/app.py
```

**Terminal mode:**

```bash
python main.py
```

Progress (feedback, skill history, topic weights) is saved to `data/`.

## Configuration

Settings live in `config.py`:

| Setting | Default | Purpose |
|---|---|---|
| `MODEL` | `qwen2.5-coder:3b` | Ollama model used for generation |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama endpoint |
| `STARTING_SKILL` | `800` | Initial skill rating |
| `TARGET_SOLVE_RATE` | `0.60` | Solve rate the difficulty aims for |
| `CODE_TIMEOUT_SECONDS` | `5` | Time limit for running code |

## Project structure

```
generator/       problem generation and validation
judge/           runs code against test cases
meta_learning/   skill rating and topic weights
feedback/        stores session feedback
web/             Flask app
templates/       web UI
main.py          terminal entry point
config.py        settings
```
