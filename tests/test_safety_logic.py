from app.services import breaker, chat_safety, ratelimit_core, secrets_check


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


def test_breaker_opens_after_repeated_failures_and_recovers():
    clock = Clock()
    gate = breaker.Breaker(threshold=2, cooldown=60, clock=clock)
    assert gate.allow()
    gate.failure()
    assert gate.allow()
    gate.failure()
    assert gate.is_open() and not gate.allow()
    clock.now += 59
    assert not gate.allow()
    clock.now += 2
    assert gate.allow()
    gate.success()
    gate.failure()
    assert gate.allow()


def test_llm_question_generation_is_off_unless_explicitly_enabled():
    from app.config import settings
    from app.engine import llm_remediation
    assert settings.llm_questions_enabled is False
    llm_remediation._client_checked = False
    llm_remediation._client = None
    assert llm_remediation._get_client() is None
