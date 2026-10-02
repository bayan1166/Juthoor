import random
from datetime import datetime, timedelta

from app.engine import adaptive_engine as ae
from app.engine import knowledge_graph as kg
from app.services import avatar_render, class_analytics, plan_rules, quiz_scoring, tree_service
from app.services import curriculum_map as cur


def test_plan_expiry_downgrades_to_basic():
    now = datetime(2026, 10, 1, 12, 0)
    assert plan_rules.plan_from_fields("pro", now + timedelta(days=3), now) == "pro"
    assert plan_rules.plan_from_fields("pro", now - timedelta(seconds=1), now) == "basic"
    assert plan_rules.plan_from_fields("school", None, now) == "school"
    assert plan_rules.plan_from_fields("basic", None, now) == "basic"


def test_trial_days_left_rounds_up_and_expires():
    now = datetime(2026, 10, 1, 12, 0)
    assert plan_rules.trial_days_left(now + timedelta(days=14), now) == 14
    assert plan_rules.trial_days_left(now + timedelta(hours=2), now) == 1
    assert plan_rules.trial_days_left(now - timedelta(minutes=1), now) is None
    assert plan_rules.trial_days_left(None, now) is None


def test_daily_quota_resets_at_local_midnight():
    assert plan_rules.day_start_utc(datetime(2026, 10, 1, 22, 0)) == datetime(2026, 10, 1, 21, 0)
    assert plan_rules.day_start_utc(datetime(2026, 10, 1, 10, 0)) == datetime(2026, 9, 30, 21, 0)


def test_gap_chain_is_masked_for_basic_plan():
    events = [1, 2, 3, 4]
    assert plan_rules.mask_drilldowns(events, True) == (events, 0)
    shown, hidden = plan_rules.mask_drilldowns(events, False)
    assert shown == [1] and hidden == 3
    assert plan_rules.mask_drilldowns([], False) == ([], 0)


def test_forecast_and_prices():
    assert plan_rules.forecast_days(9, 3.0) == 3
    assert plan_rules.forecast_days(1, 0.4) == 3
    assert plan_rules.forecast_days(5, 0) is None
    assert plan_rules.price_for("pro", "monthly") == 2990
    assert plan_rules.price_for("pro", "yearly") == 29900
    assert plan_rules.price_for("school", "monthly") == 6990


def test_catalogue_is_consistent():
    ids = [p["id"] for p in plan_rules.PLAN_CATALOG]
    assert ids == ["basic", "pro", "school"]
    for plan in plan_rules.PLAN_CATALOG:
        assert plan["id"] in plan_rules.LIMITS
        assert any(f["included"] for f in plan["features"])
    assert plan_rules.PLAN_CATALOG[1]["price_year"] < plan_rules.PLAN_CATALOG[1]["price_month"] * 12


def test_quiz_scoring_modes():
    qs = [{"id": f"q{i}", "correct_index": 1, "points": 100} for i in range(4)]
    answers = {"q0": 1, "q1": 1, "q2": 0, "q3": 1}
    plain = quiz_scoring.score_attempt(qs, answers, 30.0, "quiz", 0)
    assert plain["score"] == 300 and plain["correct"] == 3 and plain["bonus"] == 0
    fast = quiz_scoring.score_attempt(qs, answers, 10.0, "race", 120)
    slow = quiz_scoring.score_attempt(qs, answers, 110.0, "race", 120)
    assert fast["score"] > slow["score"] > 300
    none = quiz_scoring.score_attempt(qs, {}, 5.0, "race", 60)
    assert none["score"] == 0 and none["bonus"] == 0
    missing = quiz_scoring.score_attempt(qs, {"q0": 1, "zzz": 5}, 5.0, "quiz", 0)
    assert missing["correct"] == 1


def test_generated_quiz_questions_are_valid_for_every_skill():
    for skill in kg.SKILLS:
        items = quiz_scoring.generate_questions(skill, 6, random.Random(7))
        assert len(items) == 6, skill
        for item in items:
            assert len(set(item["options"])) == len(item["options"]) >= 3
            assert item["options"][item["correct_index"]]


def test_ranking_handles_ties_and_speed():
    rows = [
        {"full_name": "a", "score": 300, "duration_seconds": 50.0},
        {"full_name": "b", "score": 300, "duration_seconds": 40.0},
        {"full_name": "c", "score": 500, "duration_seconds": 90.0},
        {"full_name": "d", "score": 300, "duration_seconds": 40.0},
    ]
    ranked = class_analytics.rank_rows(rows)
    assert [r["full_name"] for r in ranked][0] == "c"
    assert [r["rank"] for r in ranked] == [1, 2, 2, 4]


def test_risk_levels():
    assert class_analytics.risk_level(0.9, 0, None, 0) == "inactive"
    assert class_analytics.risk_level(0.8, 40, 1, 1) == "high"
    assert class_analytics.risk_level(0.2, 40, 1, 0) == "high"
    assert class_analytics.risk_level(0.4, 40, 1, 0) == "medium"
    assert class_analytics.risk_level(0.8, 40, 9, 0) == "high"
    assert class_analytics.risk_level(0.8, 40, 1, 0) == "low"


def test_tree_payload_for_new_student():
    state = ae.StudentState(current_skill="absolute_value", difficulty=1)
    tree = tree_service.build_tree(state, True)
    assert [u["no"] for u in tree["units"]] == [1, 2, 3, 4]
    lessons = [l for u in tree["units"] for l in u["lessons"]]
    assert len(lessons) == 18
    first = lessons[0]
    assert first["key"] == "u1l1" and first["status"] == "open" and first["current"] is True
    assert first["concepts"] and first["concepts"][0]["segments"]
    assert tree["root_gap"]["found"] is False
    assert all(l["status"] == "soon" for l in lessons if l["skill"] is None)


def test_tree_hides_the_gap_for_basic_viewers():
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    state.gaps.add("absolute_value")
    full = tree_service.build_tree(state, True)
    locked = tree_service.build_tree(state, False)
    assert full["root_gap"]["skill"] == "absolute_value" and full["root_gap"]["steps_back"] == 4
    assert locked["root_gap"]["locked"] is True and locked["root_gap"]["skill"] is None
    assert any(l["gap"] for u in full["units"] for l in u["lessons"])
    assert not any(l["gap"] for u in locked["units"] for l in u["lessons"])


def test_math_segments_split_correctly():
    parts = cur.segments("معكوس [[5]] هو [[−5]] تماماً")
    assert [p["m"] for p in parts] == [False, True, False, True, False]
    assert parts[1]["t"] == "5"
    assert cur.plain("a [[b]] c") == "a b c"


def test_avatar_render_is_cached_and_unique_per_uid():
    cfg = {"gender": "بنت", "skin": "edb98a", "clothing": "shirtCrewNeck", "accessories": "blank",
           "top": "none", "hair": "straight", "hair_color": "black", "neck": "none"}
    one = avatar_render.render(cfg, "u1")
    two = avatar_render.render(cfg, "u2")
    assert one.startswith("<svg") and "u1" in one and "u2" not in one
    assert two != one
    assert avatar_render.render(cfg, "u1") is one


def test_unit_two_is_live_and_chained_to_integers():
    live = [l.skill for _, l in cur.all_lessons() if l.skill]
    assert len(live) == 9 and set(live) == set(kg.SKILLS)
    assert kg.prerequisites("fractions_addsub") == ["mult_div_integers"]
    assert kg.depth("mixed_div") == 8
    assert {"fractions_addsub", "mixed_addsub", "mixed_mult"} <= kg.ancestors("mixed_div")
    for key in ("u2l1", "u2l2", "u2l3", "u2l4"):
        assert cur.CONCEPTS[key]


def test_fraction_bank_covers_every_level_and_is_mathematically_consistent():
    import math
    import re
    from app.engine import offline_bank as ob
    for skill in ("fractions_addsub", "mixed_addsub", "mixed_mult", "mixed_div"):
        assert sorted(ob.REGISTRY[skill]) == [1, 2, 3]
        for level, templates in ob.REGISTRY[skill].items():
            assert len(templates) >= 3
            for template in templates:
                misses = 0
                for seed in range(60):
                    q = ob._finish(template, random.Random(seed))
                    if q is None:
                        misses += 1
                        continue
                    correct = ob.norm(q["correct_answer"])
                    others = [ob.norm(d["text"]) for d in q["distractors"]]
                    assert correct not in others and len(set(others)) == len(others)
                    raw = q["correct_answer"].replace(ob.LRI, "").replace(ob.PDI, "")
                    found = re.fullmatch(r"(\d+)/(\d+)", raw)
                    if found and q["pattern"] != "ma_convert":
                        assert math.gcd(int(found.group(1)), int(found.group(2))) == 1, raw
                    assert "/0" not in raw and not raw.startswith("-")
                assert misses <= 6, (template.fn.__name__, misses)


def test_tree_health_and_summary_cover_nine_live_skills():
    state = ae.StudentState(current_skill="fractions_addsub", difficulty=1)
    for skill in ("absolute_value", "comparing_integers", "adding_integers"):
        state.mastered.add(skill)
    assert abs(ae.tree_health(state) - 3 / 9) < 1e-9
    assert cur.summary(state)["live"] == 9


def test_correct_answers_return_the_student_up_after_a_probe():
    state = ae.StudentState(current_skill="mult_div_integers", difficulty=1)
    ae.decide_next(state, False)
    assert state.current_skill == "subtracting_integers"
    moves = [ae.decide_next(state, True).action for _ in range(6)]
    assert "backtrack" not in moves


def test_engine_alone_does_not_name_a_gap_from_a_single_error():
    state = ae.StudentState(current_skill="fractions_addsub", difficulty=1)
    state.mastered.update({"absolute_value", "comparing_integers", "adding_integers", "subtracting_integers", "mult_div_integers"})
    first = ae.decide_next(state, False)
    assert first.action == "retry" and not state.gaps
    ae.decide_next(state, False)
    third = ae.decide_next(state, False)
    assert third.action == "remediate" and state.gaps == {"fractions_addsub"}


def test_seed_story_helpers_exist_and_target_the_right_lessons():
    import ast
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "scripts" / "seed_demo.py").read_text(encoding="utf-8")
    funcs = {n.name: ast.get_source_segment(source, n) for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)}
    assert "adding_integers" in funcs["prepare_story_student"] and "place_student(db, student, start)" in funcs["prepare_story_student"]
    assert "pending_question = None" in funcs["place_student"] and "current_skill = skill" in funcs["place_student"]
    assert 'prepare_story_student(db, s2, "mult_div_integers")' in source
    assert 'prepare_story_student(db, s6, "subtracting_integers")' in source
