import ast
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def count_tests(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name.startswith("test_"))


def run(cmd, cwd=ROOT):
    try:
        done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=900)
        return done.returncode, (done.stdout + done.stderr).strip()
    except Exception as exc:
        return 99, f"{type(exc).__name__}: {exc}"


def last_line(text):
    lines = [l for l in text.splitlines() if l.strip()]
    return lines[-1] if lines else "(no output)"


def main():
    py = sorted((ROOT / "tests").glob("test_*.py"))
    rows = [(p.name, count_tests(p)) for p in py]
    code_py, out_py = run([sys.executable, "-m", "pytest", "-q"])
    js_rows = []
    for name in ("smoke.mjs", "main_smoke.mjs", "judge_smoke.mjs"):
        code, out = run(["node", name], cwd=ROOT / "tests" / "js")
        found = re.findall(r"(\d+)/(\d+) .*?checks passed", out)
        js_rows.append((name, "PASS" if code == 0 else "FAIL", f"{found[-1][0]}/{found[-1][1]}" if found else last_line(out)))
    lines = [
        "# Test report",
        "",
        f"Generated: {datetime.now():%Y-%m-%d %H:%M}",
        "",
        "## Backend (pytest)",
        "",
        f"Result: `{last_line(out_py)}` (exit code {code_py})",
        "",
        "| File | Test functions |",
        "|---|---|",
    ]
    lines += [f"| {n} | {c} |" for n, c in rows]
    lines += ["", f"Total: {sum(c for _, c in rows)} test functions.", "", "## Frontend (fake DOM, node)", "", "| Suite | Status | Checks |", "|---|---|---|"]
    lines += [f"| {n} | {s} | {c} |" for n, s, c in js_rows]
    lines += [
        "",
        "## What is covered",
        "",
        "- Learning engine: adaptive decisions, backtracking to the root, gap detection, mastery inference.",
        "- Question bank: every template of all 9 lessons generates valid questions (distinct options, simplified fraction answers, no zero denominators).",
        "- Offline tutor: step-by-step solutions for integers and fractions, misconception notes, answer grading.",
        "- Tutor guardrail: off-topic and injection phrases get the fixed fallback, curriculum phrases pass.",
        "- Safety: chat filter, blocking, reporting, teacher review, lockout, rate limits, secret strength.",
        "- API: auth, roles and permissions, plans and quotas, classrooms, quizzes, assignments, remediation.",
        "- UI: every screen with a mocked API, including the root-scan animation, loading states and error messages.",
        "",
        "## End-to-end check against a running server",
        "",
        "`python scripts/preflight.py` runs about 40 live checks (login, tree, adaptive flow, tutor, invalid inputs, teacher dashboard).",
        "",
    ]
    (ROOT / "docs" / "TEST_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    return 0 if code_py == 0 and all(s == "PASS" for _, s, _ in js_rows) else 1


if __name__ == "__main__":
    sys.exit(main())
