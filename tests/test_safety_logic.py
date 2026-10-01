import random
from datetime import datetime

from app.services import chat_safety, ratelimit_core, remediation, secrets_check


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_sliding_window_blocks_then_recovers():
    clock = Clock()
    limiter = ratelimit_core.SlidingWindow(clock)
    for _ in range(3):
        assert limiter.hit("k", 3, 60) == (True, 0)
    allowed, retry = limiter.hit("k", 3, 60)
    assert allowed is False and 1 <= retry <= 61
    clock.now += 30
    assert limiter.hit("k", 3, 60)[0] is False
    clock.now += 31
    assert limiter.hit("k", 3, 60)[0] is True


def test_sliding_window_keys_are_independent_and_clearable():
    limiter = ratelimit_core.SlidingWindow(Clock())
    for _ in range(2):
        limiter.hit("a", 2, 60)
    assert limiter.hit("a", 2, 60)[0] is False
    assert limiter.hit("b", 2, 60)[0] is True
    limiter.clear("a")
    assert limiter.hit("a", 2, 60)[0] is True


def test_failure_tracking_counts_and_expires():
    clock = Clock()
    limiter = ratelimit_core.SlidingWindow(clock)
    for _ in range(5):
        limiter.record("fail:x", 900)
    assert limiter.count("fail:x", 900) == 5
    assert limiter.retry_after("fail:x", 900) >= 1
    clock.now += 901
    assert limiter.count("fail:x", 900) == 0
    assert limiter.count("never-seen", 900) == 0


def test_purge_removes_idle_keys():
    clock = Clock()
    limiter = ratelimit_core.SlidingWindow(clock)
    for i in range(1500):
        limiter.hit(f"k{i}", 5, 10)
    clock.now += 100
    for _ in range(600):
        limiter.hit("live", 1000, 10)
    assert len(limiter._hits) < 100


def test_chat_filter_blocks_links_and_contact_details():
    blocked = [
        "زوروا www.example.com", "https://t.me/abc", "my site is cool.io", "راسلني a.b@mail.com",
        "0791234567", "\u0660\u0667\u0669\u0661\u0662\u0663\u0664\u0665\u0666\u0667", "اتصل بي 07 9123 4567", "+962 79 123 4567",
        "ضيفني على واتساب", "snapchat اضافني",
    ]
    for text in blocked:
        assert chat_safety.blocked_reason(text), text


def test_chat_filter_allows_normal_and_math_messages():
    allowed = [
        "مرحبا كيف حالك", "7 + (-3) = 4", "12 + 34 + 56 + 78", "الجواب 123456", "حليت التمرين رقم 5 صفحة 24",
        "3/4 + 1/2 = 5/4", "هل نلعب سباق الجمع؟", "اعطني الحل 1.5",
    ]
    for text in allowed:
        assert chat_safety.blocked_reason(text) is None, text


def test_secret_strength_rules():
    assert secrets_check.weak_secret_reason("change-me")
    assert secrets_check.weak_secret_reason("REPLACE_WITH_48_RANDOM_CHARS_xx")
    assert secrets_check.weak_secret_reason("short")
    assert secrets_check.weak_secret_reason("a" * 40)
    assert secrets_check.weak_secret_reason("skadjbkhabsuibdckbaskbkdjbckdsjabvhaiuuWDBXHsdjbvaedskhbvQEjabchvsfjk") is None
    assert secrets_check.weak_secret_reason(secrets_check.suggestion()) is None


def test_remediation_targets_only_students_with_the_gap():
    def overview(status):
        return {"skills": [{"skill_id": "adding_integers", "status": status}, {"skill_id": "absolute_value", "status": "mastered"}]}
    overviews = {"a": overview("gap"), "b": overview("learning"), "c": overview("gap")}
    assert remediation.students_with_gap(overviews, "adding_integers") == ["a", "c"]
    assert remediation.students_with_gap(overviews, "absolute_value") == []
    built = remediation.build_remediation("adding_integers", datetime(2026, 10, 1, 9, 0), due_days=3)
    assert built["kind"] == "remediation" and built["title"].startswith("تقوية")
    assert built["due_at"] == datetime(2026, 10, 4, 9, 0) and built["tip"]
    assert "الباقة" not in built["description"]
