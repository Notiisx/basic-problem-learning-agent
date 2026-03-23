"""
code_runner.py
Sandboxed execution of student-submitted code.
Returns stdout, stderr, and whether the answer matched expected output.
"""

import os
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
        suffix=".py", mode="w", delete=False
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
            ["python3", fname],
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
        os.unlink(fname)

    return result


def check_answer(student_output: str, expected: str) -> bool:
    """Case-insensitive whitespace-normalized comparison."""
    return student_output.strip().lower() == expected.strip().lower()
