from app.services.rag.socratic import _parse


def test_parses_plain_json():
    t = _parse('{"reply": "فكّر", "gap_detected": true, "gap_skill": "adding_integers"}', [])
    assert t.reply == "فكّر" and t.gap_detected and t.gap_skill == "adding_integers"


def test_parses_json_wrapped_in_prose():
    t = _parse('Sure!\n```json\n{"reply": "ok", "gap_detected": false}\n```', [])
    assert t is not None and t.reply == "ok"


def test_unknown_skill_is_not_a_gap():
    t = _parse('{"reply": "ok", "gap_detected": true, "gap_skill": "calculus"}', [])
    assert t.gap_detected is False and t.gap_skill == ""


def test_garbage_returns_none():
    assert _parse("not json at all", []) is None
