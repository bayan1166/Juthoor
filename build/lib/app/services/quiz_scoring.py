import random

from app.engine import offline_bank as ob


def score_attempt(questions: list[dict], answers: dict, duration_s: float, mode: str, time_limit_s: int) -> dict:
    total = len(questions)
    correct = 0
    base = 0
    for q in questions:
        picked = answers.get(str(q["id"]))
        if picked is not None and picked == q["correct_index"]:
            correct += 1
            base += q["points"]
    bonus = 0
    if mode == "race" and base > 0 and total > 0:
        limit = time_limit_s if time_limit_s > 0 else 30 * total
        speed = max(0.0, 1.0 - min(duration_s, limit) / limit)
        bonus = int(round(base * 0.5 * speed))
    return {"score": base + bonus, "correct": correct, "total": total, "base": base, "bonus": bonus}


def generate_questions(skill_id: str, count: int, rng: random.Random) -> list[dict]:
    out: list[dict] = []
    seen: list[str] = []
    attempts = 0
    while len(out) < count and attempts < count * 25:
        attempts += 1
        level = ((len(out) + attempts // 8) % 3) + 1
        q = ob.generate_offline(skill_id, level, rng, avoid=seen)
        if q.get("type", "mcq") != "mcq":
            continue
        if q["question"] in seen:
            continue
        options = [q["correct_answer"]] + [d["text"] for d in q.get("distractors", [])]
        if len(set(options)) < 3:
            continue
        rng.shuffle(options)
        seen.append(q["question"])
        out.append({
            "prompt": q["question"],
            "options": options,
            "correct_index": options.index(q["correct_answer"]),
            "points": 100,
        })
    return out
