"""Generated-question integrity across the whole offline bank (every skill, every level).

Checks: a question and answer exist, distractors never equal the correct answer (after
normalisation), MCQ options are distinct, and no answer contains a zero denominator.
Run with BANK_SAMPLES=20000 for the long version quoted in the docs.
"""
import os
import random
import re

import pytest

from app.engine import offline_bank as ob

SAMPLES = int(os.environ.get("BANK_SAMPLES", "1500"))
ZERO_DEN = re.compile(r"/\s*0(?![0-9])")


@pytest.mark.parametrize("skill", sorted(ob.REGISTRY))
def test_generated_questions_are_well_formed(skill):
    rng = random.Random(2076)
    levels = sorted(ob.REGISTRY[skill])
    per_level = max(1, SAMPLES // (len(ob.REGISTRY) * len(levels)))
    for level in levels:
        for _ in range(per_level):
            q = ob.generate_offline(skill, level, rng)
            assert q["question"] and str(q["correct_answer"]).strip()
            correct = ob.norm(q["correct_answer"])
            wrongs = [ob.norm(d["text"]) for d in q.get("distractors", [])]
            assert correct not in wrongs, q
            assert len(wrongs) == len(set(wrongs)), q
            assert not ZERO_DEN.search(ob.norm(q["correct_answer"])), q
