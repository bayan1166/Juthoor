DEFAULT_START_SKILL = "absolute_value"
START_DIFFICULTY = 1
MIN_DIFFICULTY = 1
MAX_DIFFICULTY = 3
PROBE_DIFFICULTY = 1
SESSION_LENGTH = 5

MASTERY_THRESHOLD = 0.85


BKT = {
    "p_init": 0.3,
    "p_slip": 0.1,
    "p_guess": 0.2,
    "p_learn": 0.2
}


MAX_DRILL_DEPTH = 4


MIN_CHAIN_EVIDENCE = 3

# A single wrong probe is not enough to blame a skill: the root needs this many wrong answers.
MIN_ROOT_EVIDENCE = 2

# A mastered skill whose BKT estimate falls below this is treated as contested again.
CONTEST_THRESHOLD = 0.5


LLM = {
    "enabled": True,
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "timeout_seconds": 4,
}
