"""Teacher-blind diagnosis comparison.

Protocol (docs/PILOT.md, section "Teacher-blind comparison"):
1. BEFORE opening Juthoor's report, the teacher writes, for each learner code, the
   prerequisite lesson she believes is the underlying gap (column teacher_root).
2. Then copy Juthoor's named root for the same learner (teacher drawer, "سجل التشخيص",
   or the class CSV export) into juthoor_root.
3. python scripts/agreement_summary.py docs/teacher_agreement_template.csv

Cells may hold skill ids (adding_integers) or Arabic lesson names. Empty cells are skipped.
"none" means "no gap / insufficient evidence". The output is raw agreement on a small sample:
an early signal, not a validated accuracy figure.
"""
import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.engine import knowledge_graph as kg

NONE_WORDS = {"none", "no_gap", "insufficient", "لا يوجد", "لا فجوة", "-"}


def normalise(value: str):
    v = (value or "").strip()
    if not v:
        return None
    if v.lower() in NONE_WORDS:
        return "none"
    if v in kg.SKILLS:
        return v
    for sid, skill in kg.SKILLS.items():
        if v == skill.name_ar or v.lower() == skill.name.lower():
            return sid
    return f"unknown:{v}"


def summarize(rows):
    usable, skipped, unknown = [], [], []
    for row in rows:
        code = (row.get("student_code") or "").strip() or f"#{len(usable) + len(skipped) + 1}"
        teacher, juthoor = normalise(row.get("teacher_root")), normalise(row.get("juthoor_root"))
        if teacher is None or juthoor is None:
            skipped.append(code)
            continue
        for value in (teacher, juthoor):
            if value.startswith("unknown:"):
                unknown.append(f"{code}: {value[8:]}")
        usable.append((code, teacher, juthoor))
    n = len(usable)
    agree = [u for u in usable if u[1] == u[2]]
    # "Adjacent" = one names a direct prerequisite of the other (same chain, one step apart).
    adjacent = [u for u in usable if u[1] != u[2] and u[1] in kg.SKILLS and u[2] in kg.SKILLS
                and (u[1] in kg.prerequisites(u[2]) or u[2] in kg.prerequisites(u[1]))]
    return {"n": n, "agree": len(agree), "adjacent": len(adjacent), "skipped": skipped, "unknown": unknown,
            "disagreements": [u for u in usable if u[1] != u[2]]}


def report(s) -> str:
    if s["n"] == 0:
        return "No complete rows yet. Fill teacher_root and juthoor_root."
    lines = [
        f"learners compared: {s['n']}",
        f"exact agreement:   {s['agree']}/{s['n']}",
        f"one step apart:    {s['adjacent']}/{s['n']} (teacher and Juthoor named neighbouring lessons)",
    ]
    if s["disagreements"]:
        lines.append("disagreements (review these with the teacher):")
        lines += [f"  {code}: teacher={t} juthoor={j}" for code, t, j in s["disagreements"]]
    if s["unknown"]:
        lines.append("unrecognised lesson names: " + "; ".join(s["unknown"]))
    if s["skipped"]:
        lines.append("skipped (incomplete): " + ", ".join(s["skipped"]))
    lines.append(f"Note: a sample of {s['n']} is an early agreement signal only, not a measure of diagnostic accuracy.")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("csv_path")
    args = parser.parse_args(argv)
    with open(args.csv_path, newline="", encoding="utf-8-sig") as fh:
        print(report(summarize(list(csv.DictReader(fh)))))


if __name__ == "__main__":
    main()
