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

MATH_PROMPT = """You are an expert competitive math problem writer.

Generate a rigorous math problem with the following properties:
  Topic:      {topic}
  Difficulty: {difficulty} (on an ELO scale; 1200 = intermediate)

You MUST respond in exactly this format and nothing else:

PROBLEM:
<full problem statement, clearly worded, with a concrete numerical answer>

CONSTRAINTS:
<any numerical constraints, e.g. 1 ≤ n ≤ 10^9>

SOLUTION_EXPLANATION:
<step-by-step solution explanation>

SOLUTION_CODE:
```python
<a complete, runnable Python solution that reads from stdin and prints the answer>
```

TEST_CASES:
<input1> | <expected_output1>
<input2> | <expected_output2>
<input3> | <expected_output3>

Make sure SOLUTION_CODE reads input with input() and prints a single answer line.
Make sure each TEST_CASE input matches exactly what the code reads.
"""

PROG_PROMPT = """You are an expert competitive programming problem setter.

Generate a competitive programming problem with the following properties:
  Topic:      {topic}
  Difficulty: {difficulty} (on an ELO scale; 1200 = intermediate Codeforces)

You MUST respond in exactly this format and nothing else:

PROBLEM:
<full problem statement with example input/output>

CONSTRAINTS:
<time limit, memory limit, variable ranges>

SOLUTION_EXPLANATION:
<algorithm walkthrough>

SOLUTION_CODE:
```python
<a complete, runnable Python solution that reads from stdin and prints the answer>
```

TEST_CASES:
<input1> | <expected_output1>
<input2> | <expected_output2>
<input3> | <expected_output3>

Make sure SOLUTION_CODE reads from stdin with input() and prints the answer.
Make sure each TEST_CASE uses exactly the input format the code expects.
"""


def _call_llm(prompt: str) -> str:
    """Raw call to Ollama API. Returns the model's text response."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=120,
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

    # Extract solution code separately (inside ```python ... ```)
    code_match = re.search(r"```python\s*(.*?)```", raw, re.DOTALL)
    solution_code = code_match.group(1).strip() if code_match else ""

    # Parse test cases: each line is "input | expected_output"
    test_block = extract("TEST_CASES")
    test_cases = []
    for line in test_block.splitlines():
        line = line.strip()
        if "|" in line:
            parts = line.split("|", 1)
            inp = parts[0].strip()
            out = parts[1].strip()
            if inp and out:
                test_cases.append((inp, out))

    return {
        "statement":            extract("PROBLEM"),
        "constraints":          extract("CONSTRAINTS"),
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
