"""Run the reproducible diagnostic benchmark and print/save a JSON report.

    python scripts/diagnostic_benchmark.py [--reps 5] [--out benchmarks/latest.json]

Synthetic learners only. See app/engine/benchmark.py for what the numbers do and do not mean.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.engine import benchmark  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    rep = benchmark.report(a.reps)
    text = json.dumps(rep, indent=2, ensure_ascii=False)
    print(text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    return 0 if rep.get("deterministic", True) else 1

if __name__ == "__main__":
    raise SystemExit(main())
