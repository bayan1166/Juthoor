# Competitive advantage: evidence-first root diagnosis

## The claim (and its limits)

Juthoor's differentiator is **how it decides**, not how many lessons it has: it names a root learning gap only when
the evidence supports it, says exactly what evidence is still missing when it does not, and abstains instead of guessing.
This is implemented in the engine, demoable, and measured on a reproducible synthetic benchmark.

Not claimed: that it beats any named competitor (no competitor was tested), that it reaches a given accuracy on real
students (no field data exists), or that the synthetic numbers transfer to a classroom.

## What is built

| Capability | Where | How to see it |
|---|---|---|
| A single lucky correct answer does not clear a prerequisite (needs `MIN_SOLID_EVIDENCE` = 2 correct, none wrong) | `app/engine/diagnosis.py::solid` | `tests/test_diagnosis_flow.py::test_one_lucky_correct_prerequisite_answer_does_not_clear_the_prerequisite` |
| Likelihood ratio of the leading candidate vs "no gap", in log space; a root needs LR >= `MIN_ROOT_LR` (20) | `diagnosis.likelihood_ratio` | verdict field `likelihood_ratio` |
| Abstention with a machine-readable reason: `insufficient_evidence` | `diagnosis.diagnose` | `evidence_status.status` in every answer response |
| "What would settle it": `evidence_needed` (`more_errors`, `confirm_root`, `verify_prerequisite`, `resolve_mixed`, each with skill and minimum count) | `diagnosis.evidence_needed` | shown to the learner under the evidence banner ("ما يلزم لحسم التشخيص"); `tests/test_evidence_needed.py` |
| Evidence, path, confidence level and outcome shown to the teacher | `engine_bridge.diagnosis_history`, teacher drawer | teacher view of any diagnosed learner |
| Reproducible benchmark with known ground truth | `app/engine/benchmark.py`, `scripts/diagnostic_benchmark.py` | `python scripts/diagnostic_benchmark.py --reps 5` |
| Threshold sensitivity sweep | `scripts/benchmark_sweep.py` -> `benchmarks/sweep.json` | trade-off between abstention and false diagnosis |

## Measured effect on the synthetic benchmark (same learners, same seeds, 810 cases)

| Scenario | Metric | Before | After |
|---|---|---|---|
| Known root, clean answers | root correct when it names one | 79.9 % | 97.1 % |
| | wrong root (share of gap cases) | 19.1 % | 2.7 % |
| | premature declaration (prerequisites barely observed) | 50.0 % | 0.0 % |
| Known root, noisy | wrong root | 28.4 % | 7.6 % |
| Lucky-correct learner | wrong root | 39.6 % | 30.2 % |
| No gap | false diagnosis (clean / noisy / very noisy) | 2.2 / 8.9 / 20.0 % | 2.2 / 8.9 / 20.0 % (unchanged) |

Trade-off: abstention in known-root cases rose from 4.9 % to 7.6 % (clean) because the engine now asks for more evidence.
Confidence levels are better ordered than before (high 86.3 %, medium 80.0 % correct on the benchmark; before 77.2 % / 61.1 %).

Honest gaps: the 95 % target was **not** reached (clean 97.1 % when committed but 89.8 % overall; noisy 91.1 % / 77.8 %); the
lucky-correct scenario is still poor (30.2 % wrong root); and the false-diagnosis rate on learners with no gap was not improved
at the shipped thresholds. Stricter thresholds (`benchmarks/sweep.json`: LR 100 or 400) cut the noisy no-gap false diagnosis from
11.1 % to 3.7 % / 0.0 % at the price of 1-4 points more abstention; they were not shipped because they changed product behaviour
covered by existing tests, and because the benchmark is synthetic.

## What would make it a real advantage

1. A teacher-labelled pilot (`docs/PILOT.md`, `docs/teacher_agreement_template.csv`) to measure agreement on real learners.
2. Calibrating BKT and the evidence thresholds on that data.
3. Comparing against a simple baseline (last-N answers) on the same data - the engine-level comparison is in `tests/test_bkt_properties.py`.
