"""
code_runner.py
Sandboxed execution of student-submitted code.
Returns stdout, stderr, and whether the answer matched expected output.
"""

import os
import sys
import tempfile
import subprocess
from config import CODE_TIMEOUT_SECONDS


def run_student_code(code: str, input_data: str) -> dict:
    """
    Execute student code with given input in a sandboxed subprocess.

    Returns dict with:
        stdout   : program output
        stderr   : error output (empty on success)
        timed_out: bool
        error    : any exception message
    """
    with tempfile.NamedTemporaryFile(
        suffix=".py", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(code)
        fname = f.name

    result = {
        "stdout": "",
        "stderr": "",
        "timed_out": False,
        "error": "",
    }

    try:
        proc = subprocess.run(
            # FIX: use sys.executable instead of hardcoded "python3"
            [sys.executable, fname],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=CODE_TIMEOUT_SECONDS,
        )
        result["stdout"] = proc.stdout.strip()
        result["stderr"] = proc.stderr.strip()
    except subprocess.TimeoutExpired:
        result["timed_out"] = True
        result["error"] = f"Time limit exceeded ({CODE_TIMEOUT_SECONDS}s)"
    except Exception as e:
        result["error"] = str(e)
    finally:
        try:
            os.unlink(fname)
        except OSError:
            pass

    return result


def check_answer(student_output: str, expected: str) -> bool:
    """Case-insensitive whitespace-normalized comparison."""
    return student_output.strip().lower() == expected.strip().lower()


def judge_against_test_cases(
    code: str, test_cases: list[tuple[str, str]]
) -> dict:
    """
    Run student code against all problem test cases.

    Returns:
        verdict: "PASS" | "WRONG_ANSWER" | "RUNTIME_ERROR" | "TLE"
        passed:  int (number of passing tests)
        total:   int
        details: list of per-test dicts
    """
    if not test_cases:
        # No test cases — just try to run the code with empty input
        r = run_student_code(code, "")
        if r["timed_out"]:
            return {"verdict": "TLE", "passed": 0, "total": 0, "details": []}
        if r["error"] or r["stderr"]:
            return {
                "verdict": "RUNTIME_ERROR",
                "passed": 0, "total": 0,
                "details": [{"test": 1, "verdict": "RUNTIME_ERROR",
                              "error": r["error"] or r["stderr"]}],
            }
        return {"verdict": "PASS", "passed": 0, "total": 0, "details": []}

    details = []
    passed = 0

    for i, (inp, expected) in enumerate(test_cases, 1):
        r = run_student_code(code, inp)

        if r["timed_out"]:
            details.append({"test": i, "verdict": "TLE"})
            # Count remaining as TLE too
            for j in range(i + 1, len(test_cases) + 1):
                details.append({"test": j, "verdict": "TLE"})
            return {
                "verdict": "TLE",
                "passed": passed,
                "total": len(test_cases),
                "details": details,
            }

        if r["error"] and not r["stdout"]:
            details.append({
                "test": i, "verdict": "RUNTIME_ERROR",
                "error": r["error"] or r["stderr"],
            })
            continue

        if check_answer(r["stdout"], expected):
            passed += 1
            details.append({"test": i, "verdict": "PASS"})
        else:
            details.append({
                "test": i, "verdict": "WRONG_ANSWER",
                "got": r["stdout"], "expected": expected,
            })

    overall = "PASS" if passed == len(test_cases) else (
        "RUNTIME_ERROR" if any(d["verdict"] == "RUNTIME_ERROR" for d in details)
        else "WRONG_ANSWER"
    )

    return {
        "verdict": overall,
        "passed": passed,
        "total": len(test_cases),
        "details": details,
    }
