"""
validator.py
Runs the LLM-generated reference solution against its own test cases.
Discards problems where the solution fails — prevents bad problems from
reaching the student.
"""

import os
import sys
import tempfile
import subprocess
from config import CODE_TIMEOUT_SECONDS


def _run_code(code: str, input_data: str) -> tuple[bool, str]:
    """
    Run Python code string with given stdin.
    Returns (success: bool, stdout: str).
    """
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        fname = f.name

    try:
        result = subprocess.run(
            # FIX: use sys.executable consistently (same Python that runs the app)
            [sys.executable, fname],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=CODE_TIMEOUT_SECONDS,
        )
        return True, result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    except Exception as e:
        return False, str(e)
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass


def validate_problem(problem: dict) -> tuple[bool, str]:
    """
    Validate a problem by running its solution_code against its test_cases.

    Returns:
        (True, "ok")           – all tests pass
        (False, reason_str)    – at least one test failed
    """
    code = problem.get("solution_code", "")
    test_cases = problem.get("test_cases", [])

    if not code:
        return False, "No solution code found."

    if not test_cases:
        # FIX: if LLM gave no test cases, still allow the problem through
        # (better to show an unvalidated problem than silently discard)
        return True, "ok (no test cases to validate)"

    for i, (inp, expected) in enumerate(test_cases):
        ok, output = _run_code(code, inp)
        if not ok:
            return False, f"Test {i+1} error: {output}"
        if output != expected:
            return (
                False,
                f"Test {i+1} failed.\n  Input:    {inp!r}\n"
                f"  Expected: {expected!r}\n  Got:      {output!r}",
            )

    return True, "ok"
