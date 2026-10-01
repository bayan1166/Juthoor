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


LLM = {
    "enabled": True,
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "timeout_seconds": 4,
}
