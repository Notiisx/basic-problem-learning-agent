"""
main.py  –  CLI interface for the meta-learning problem generator.

Usage (from project root):
    python main.py
"""

import sys
import time

from generator.problem_generator import generate_problem
from generator.validator import validate_problem
from meta_learning.difficulty_model import (
    get_current_skill,
    update_skill,
    recommend_difficulty,
    solve_probability,
)
# FIX: choose_topic now accepts optional forced= keyword arg
from meta_learning.topic_weights import choose_topic, update_weights, get_topic_stats
from feedback.feedback_store import store_session, get_summary
from config import MAX_VALIDATION_ATTEMPTS, TOPIC_LABELS


# ── Helpers ───────────────────────────────────────────────────────────────────

def hr(char="─", width=60):
    print(char * width)

def prompt_int(msg: str, lo: int, hi: int) -> int:
    while True:
        try:
            val = int(input(msg))
            if lo <= val <= hi:
                return val
            print(f"  Please enter a number between {lo} and {hi}.")
        except ValueError:
            print("  Invalid input.")

def prompt_yn(msg: str) -> bool:
    while True:
        ans = input(msg + " (y/n): ").strip().lower()
        if ans in ("y", "yes"):
            return True
        if ans in ("n", "no"):
            return False


# ── Main loop ─────────────────────────────────────────────────────────────────

def run():
    hr("═")
    print("  META-LEARNING PROBLEM GENERATOR")
    print("  Powered by local LLaMA via Ollama")
    hr("═")

    skill      = get_current_skill()
    difficulty = recommend_difficulty(skill)

    print(f"\n  Your current skill rating : {skill}")
    print(f"  Recommended difficulty    : {difficulty}")

    summary = get_summary()
    if summary["total"] > 0:
        print(f"  Sessions completed        : {summary['total']}")
        print(f"  Overall solve rate        : {summary['solve_rate']*100:.0f}%")

    print()

    while True:
        hr()
        # FIX: choose_topic() uses underscore keys; display with TOPIC_LABELS
        topic      = choose_topic()
        difficulty = recommend_difficulty(get_current_skill())

        display = TOPIC_LABELS.get(topic, topic.replace("_", " ").title())
        print(f"\n  Topic      : {display}")
        print(f"  Difficulty : {difficulty}  (your skill: {get_current_skill()})")
        p_solve = solve_probability(get_current_skill(), difficulty)
        print(f"  Expected solve probability: {p_solve*100:.0f}%")
        print()

        # ── Generate + validate ───────────────────────────────────────────────
        problem = None
        for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
            print(f"  Generating problem... (attempt {attempt}/{MAX_VALIDATION_ATTEMPTS})")
            try:
                candidate = generate_problem(topic, difficulty)
            except RuntimeError as e:
                print(f"\n  ERROR: {e}")
                sys.exit(1)
            except ValueError as e:
                print(f"  Generation failed: {e}  Retrying...")
                continue

            print("  Validating solution against test cases...")
            ok, reason = validate_problem(candidate)
            if ok:
                problem = candidate
                print("  ✓ Problem validated.\n")
                break
            else:
                print(f"  ✗ Validation failed: {reason}  Retrying...")

        if problem is None:
            print("  Could not generate a valid problem. Skipping this round.\n")
            continue

        # ── Display problem ───────────────────────────────────────────────────
        hr("─")
        print("\nPROBLEM\n")
        print(problem["statement"])
        print()
        print("CONSTRAINTS")
        print(problem["constraints"])
        hr("─")

        # ── Student solves ────────────────────────────────────────────────────
        hint_used  = False
        start_time = time.time()

        print("\nOptions:  [s] submit answer   [h] show hint   [q] quit\n")

        while True:
            choice = input("  > ").strip().lower()
            if choice == "q":
                print("\n  Goodbye. Keep grinding!\n")
                sys.exit(0)
            elif choice == "h":
                hint_used = True
                print("\nHINT / SOLUTION EXPLANATION:")
                print(problem["solution_explanation"])
                print()
            elif choice == "s":
                break
            else:
                print("  Enter 's' to submit, 'h' for hint, 'q' to quit.")

        elapsed = time.time() - start_time
        solved  = prompt_yn("\n  Did you solve it correctly?")

        # ── Feedback ──────────────────────────────────────────────────────────
        print("\nQuick feedback (1 = worst, 5 = best):")
        diff_rating     = prompt_int("  Difficulty felt appropriate? (1–5): ", 1, 5)
        clarity_rating  = prompt_int("  Clarity of problem statement?  (1–5): ", 1, 5)
        interest_rating = prompt_int("  How interesting was the topic?  (1–5): ", 1, 5)

        # ── Update models ─────────────────────────────────────────────────────
        skill_update = update_skill(solved, difficulty)
        update_weights(topic, solved, interest_rating)
        store_session(
            topic              = topic,
            difficulty         = difficulty,
            solved             = solved,
            solve_time_seconds = elapsed,
            difficulty_rating  = diff_rating,
            clarity_rating     = clarity_rating,
            interest_rating    = interest_rating,
            hint_used          = hint_used,
        )

        # ── Result summary ────────────────────────────────────────────────────
        hr()
        outcome = "✓ Solved!" if solved else "✗ Not solved"
        print(f"\n  {outcome}")
        print(f"  Skill: {skill_update['old_skill']}  →  {skill_update['new_skill']}"
              f"  (Δ {skill_update['delta']:+.1f})")
        print(f"  Time taken: {elapsed:.0f}s")

        if not solved:
            show = prompt_yn("\n  See the reference solution?")
            if show:
                print("\nREFERENCE SOLUTION:\n")
                print(problem["solution_explanation"])
                print()
                print("PYTHON CODE:\n")
                print(problem["solution_code"])

        # ── Topic weights recap ───────────────────────────────────────────────
        print("\nCurrent topic weights (higher = appears more often):")
        for t, w in sorted(get_topic_stats().items(), key=lambda x: -x[1]):
            label = TOPIC_LABELS.get(t, t.replace("_", " ").title())
            bar = "█" * int(w * 10)
            print(f"  {label:<30} {w:.2f}  {bar}")

        print()
        again = prompt_yn("  Next problem?")
        if not again:
            hr("═")
            s = get_summary()
            print(f"\n  Session complete.  Total: {s['total']}  Solve rate: {s['solve_rate']*100:.0f}%")
            print("  Skill history saved to data/skill_history.json\n")
            hr("═")
            break


if __name__ == "__main__":
    run()
