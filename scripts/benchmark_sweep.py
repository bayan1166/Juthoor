"""Sensitivity sweep of the evidence thresholds on the synthetic benchmark.

    python scripts/benchmark_sweep.py [--reps 3] [--out benchmarks/sweep.json]

Shows the accuracy / abstention / false-diagnosis trade-off for (MIN_SOLID_EVIDENCE, MIN_ROOT_LR).
Synthetic learners only: this documents a trade-off, it does not prove classroom accuracy.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.engine import benchmark, config  # noqa: E402

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    keep = (config.MIN_SOLID_EVIDENCE, config.MIN_ROOT_LR)
    rows = []
    try:
        for solid in (2, 3):
            for lr in (20.0, 100.0, 400.0):
                config.MIN_SOLID_EVIDENCE, config.MIN_ROOT_LR = solid, lr
                s = benchmark.summarise(benchmark.run_all(a.reps))["scenarios"]
                rows.append({
                    "min_solid_evidence": solid, "min_root_lr": lr,
                    "clean_correct_overall_pct": s["known_root_clean"]["root_accuracy_overall_pct"],
                    "clean_correct_when_committed_pct": s["known_root_clean"]["root_accuracy_when_committed_pct"],
                    "clean_wrong_pct": s["known_root_clean"]["wrong_root_rate_pct"],
                    "clean_abstain_pct": s["known_root_clean"]["abstention_rate_pct"],
                    "noisy_wrong_pct": s["known_root_noisy"]["wrong_root_rate_pct"],
                    "noisy_abstain_pct": s["known_root_noisy"]["abstention_rate_pct"],
                    "lucky_wrong_pct": s["lucky_correct"]["wrong_root_rate_pct"],
                    "no_gap_false_clean_pct": s["no_gap_clean"]["false_diagnosis_rate_pct"],
                    "no_gap_false_noisy_pct": s["no_gap_noisy"]["false_diagnosis_rate_pct"],
                    "no_gap_false_very_noisy_pct": s["no_gap_very_noisy"]["false_diagnosis_rate_pct"],
                })
    finally:
        config.MIN_SOLID_EVIDENCE, config.MIN_ROOT_LR = keep
    out = {"reps_per_cell": a.reps, "shipped": {"min_solid_evidence": keep[0], "min_root_lr": keep[1]}, "grid": rows}
    text = json.dumps(out, indent=2)
    print(text)
    if a.out:
        Path(a.out).write_text(text + "\n", encoding="utf-8")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
