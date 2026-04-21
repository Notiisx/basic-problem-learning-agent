"""
problem_generator.py
Sends a structured prompt to the local LLM (via Ollama) and returns a
parsed problem dict with: statement, constraints, solution_explanation,
solution_code, and test_cases.
"""

import re
import requests
from config import OLLAMA_URL, MODEL


# ── Topic classification ──────────────────────────────────────────────────────
# FIX: use underscore keys to match config.py TOPIC_WEIGHTS
MATH_TOPICS = {"number_theory", "combinatorics", "modular_arithmetic"}


# ── Prompt templates ──────────────────────────────────────────────────────────

MATH_PROMPT = """You are an expert competitive math problem setter writing in the style of Codeforces.

Generate a rigorous math problem with:
  Topic:      {topic}
  Difficulty: {difficulty} (ELO; 1200 = Codeforces Div.2 B)

Respond in EXACTLY this format — no extra text before or after:

TITLE:
<short memorable problem title, no letter prefix>

STATEMENT:
<Narrative problem description 2-4 paragraphs. Use $...$ for inline math (e.g. $n$, $a_i$, $1 \\le n \\le 10^9$) and $$...$$ for displayed math. Define all variables clearly. Include a concrete scenario.>

INPUT:
<Precise input format. First line contains $t$ — number of test cases ($1 \\le t \\le 100$). Then describe each test case line by line. State all variable constraints here.>

OUTPUT:
<Precise output format. One line per test case.>

NOTE:
<Explain why each example output is correct. Reference test cases by number.>

SOLUTION_EXPLANATION:
<Step-by-step algorithm.>

SOLUTION_CODE:
```python
<Complete Python solution. Read t on first line, loop t times, print answer per test case.>
```

TEST_CASES:
===
<complete stdin for judge run 1 — include t on line 1>
---
<expected stdout for run 1>
===
<complete stdin for judge run 2>
---
<expected stdout for run 2>
===
<complete stdin for judge run 3>
---
<expected stdout for run 3>

Each === block is one complete judge run. TEST_CASES must use EXACTLY the input format SOLUTION_CODE reads."""

PROG_PROMPT = """You are an expert competitive programming problem setter writing in the style of Codeforces.

Generate a competitive programming problem with:
  Topic:      {topic}
  Difficulty: {difficulty} (ELO; 1200 = Codeforces Div.2 B)

Respond in EXACTLY this format — no extra text before or after:

TITLE:
<short memorable problem title, no letter prefix>

STATEMENT:
<Narrative problem description 2-4 paragraphs. Use $...$ for inline math (e.g. $n$, $a_i$, $1 \\le n \\le 10^9$) and $$...$$ for displayed math. Define all variables and operations clearly. Use a concrete story or scenario.>

INPUT:
<Precise input format. First line contains $t$ — number of test cases ($1 \\le t \\le 100$). Then describe each test case line by line. State all variable constraints here.>

OUTPUT:
<Precise output format. One line per test case unless otherwise specified.>

NOTE:
<Explain why each example output is correct. Reference specific test cases by number.>

SOLUTION_EXPLANATION:
<Step-by-step algorithm and complexity.>

SOLUTION_CODE:
```python
<Complete Python solution. Read t on first line, loop t times, print answer per test case.>
```

TEST_CASES:
===
<complete stdin for judge run 1 — include t on line 1>
---
<expected stdout for run 1>
===
<complete stdin for judge run 2>
---
<expected stdout for run 2>
===
<complete stdin for judge run 3>
---
<expected stdout for run 3>

Each === block is one complete judge run. TEST_CASES must use EXACTLY the input format SOLUTION_CODE reads."""


def _call_llm(prompt: str) -> str:
    """Raw call to Ollama API. Returns the model's text response."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=300,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot reach Ollama. Make sure it is running: `ollama serve`"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama request timed out. The model may be too slow or overloaded.")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Ollama returned an error: {e}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Ollama request failed: {e}")
    except ValueError as e:
        raise RuntimeError(f"Ollama returned invalid JSON: {e}")


def _parse_response(raw: str) -> dict:
    """Extract structured fields from the LLM's formatted response."""
    def extract(tag: str) -> str:
        pattern = rf"{tag}:\s*(.*?)(?=\n[A-Z_]+:|$)"
        m = re.search(pattern, raw, re.DOTALL)
        return m.group(1).strip() if m else ""

    code_match = re.search(r"```python\s*(.*?)```", raw, re.DOTALL)
    solution_code = code_match.group(1).strip() if code_match else ""

    # Parse TEST_CASES: === separates runs, --- separates input from output
    test_block = extract("TEST_CASES")
    test_cases = []
    blocks = re.split(r'===', test_block)
    for block in blocks:
        block = block.strip()
        if '---' in block:
            parts = block.split('---', 1)
            inp, out = parts[0].strip(), parts[1].strip()
            if inp and out:
                test_cases.append((inp, out))

    # Fallback: old single-line "input | output" format
    if not test_cases:
        for line in test_block.splitlines():
            line = line.strip()
            if '|' in line:
                parts = line.split('|', 1)
                inp, out = parts[0].strip(), parts[1].strip()
                if inp and out:
                    test_cases.append((inp, out))

    return {
        "title":                extract("TITLE"),
        "statement":            extract("STATEMENT"),
        "input_format":         extract("INPUT"),
        "output_format":        extract("OUTPUT"),
        "note":                 extract("NOTE"),
        "constraints":          "",
        "solution_explanation": extract("SOLUTION_EXPLANATION"),
        "solution_code":        solution_code,
        "test_cases":           test_cases,
        "raw":                  raw,
    }


def generate_problem(topic: str, difficulty: int) -> dict:
    """
    Generate and parse a problem for the given topic and ELO difficulty.
    Returns a dict or raises RuntimeError on parse failure.
    """
    # FIX: MATH_TOPICS uses underscore keys matching config
    template = MATH_PROMPT if topic in MATH_TOPICS else PROG_PROMPT
    # Format topic with spaces for the prompt text (human readable)
    display_topic = topic.replace("_", " ")
    prompt = template.format(topic=display_topic, difficulty=difficulty)
    raw = _call_llm(prompt)
    problem = _parse_response(raw)

    if not problem["statement"]:
        raise ValueError("LLM response was missing the problem statement.")
    if not problem["solution_code"]:
        raise ValueError("LLM response was missing solution code.")

    return problem
