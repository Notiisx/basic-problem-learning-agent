"""
problem_generator.py
Sends a structured prompt to the local LLM (via Ollama) and returns a
parsed problem dict with: statement, constraints, solution_explanation,
solution_code, and test_cases.
"""

import re
import requests
from config import OLLAMA_URL, MODEL


# ── Prompt templates ──────────────────────────────────────────────────────────

MATH_PROMPT = """You are an expert competitive math problem writer.

Generate a rigorous math problem with the following properties:
  Topic:      {topic}
  Difficulty: {difficulty} (on an ELO scale; 1200 = intermediate)

You MUST respond in exactly this format and nothing else:

PROBLEM:
<full problem statement, clearly worded>

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
"""

MATH_TOPICS = {"number theory", "combinatorics", "modular arithmetic"}


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
        if "|" in line:
            parts = line.split("|", 1)
            test_cases.append((parts[0].strip(), parts[1].strip()))

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
    template = MATH_PROMPT if topic in MATH_TOPICS else PROG_PROMPT
    prompt = template.format(topic=topic, difficulty=difficulty)
    raw = _call_llm(prompt)
    problem = _parse_response(raw)

    if not problem["statement"] or not problem["solution_code"]:
        raise ValueError("LLM response was missing required fields.")

    return problem
