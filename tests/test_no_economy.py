"""Coins, gems, the wallet and the avatar shop are not part of the product any more.

The legacy tables stay (non-destructive), but nothing awards, spends or shows coins or gems: not the learning
flow, not registration, not the bootstrap payload, not the navigation, not the plans.
"""
import pathlib
import re
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATIC = ROOT / "app" / "static"

# Arabic and English words for the removed economy, as a learner would see them.
ECONOMY_WORDS = re.compile(r"العملات|عملات|الجواهر|جواهر|جوهرة|المتجر|متجر الشخصية|رصيدك|wallet|coins?\b|gems?\b|\+\$\{d\.(coins|gems)",
                           re.IGNORECASE)


def _frontend_sources():
    for path in sorted(STATIC.rglob("*")):
        if path.suffix in (".js", ".html", ".css") and path.is_file():
            yield path, path.read_text(encoding="utf-8")


def test_the_frontend_never_mentions_coins_gems_wallet_or_shop():
    hits = []
    for path, src in _frontend_sources():
        for m in ECONOMY_WORDS.finditer(src):
            line = src.count("\n", 0, m.start()) + 1
            hits.append(f"{path.relative_to(ROOT)}:{line}: {m.group(0)}")
    assert hits == [], hits


def test_the_shop_view_and_route_are_gone():
    assert not (STATIC / "js" / "views" / "shop.js").exists()
    main = (STATIC / "js" / "main.js").read_text(encoding="utf-8")
    assert "/shop" not in main and "shopView" not in main and "wallet" not in main
    css = (STATIC / "css" / "app.css").read_text(encoding="utf-8")
    assert ".pill.coin" not in css and ".pill.gem" not in css and ".item-card" not in css


def test_no_plan_sells_the_shop():
    from app.services import plan_rules
    blob = repr(plan_rules.PLAN_CATALOG)
    assert "متجر" not in blob and "عملات" not in blob and "جواهر" not in blob


def test_the_answer_schema_has_no_coin_fields():
    src = (ROOT / "app" / "schemas" / "adaptive.py").read_text(encoding="utf-8")
    assert "coins_awarded" not in src and "gems_awarded" not in src
    bridge = (ROOT / "app" / "services" / "engine_bridge.py").read_text(encoding="utf-8")
    assert "grant_reward" not in bridge and "coins" not in bridge


def test_registration_and_learning_write_no_wallet_rows(client, db):
    from sqlalchemy import func, select

    from app.models.economy import Wallet, WalletTransaction
    from tests.helpers import register
    s = register(client)
    sid = uuid.UUID(s["id"])
    boot = client.get(f"/students/{s['id']}/adaptive/bootstrap", headers=s["headers"]).json()
    assert "wallet" not in boot and boot["avatar_svg"].startswith("<svg")
    for _ in range(4):
        client.get(f"/students/{s['id']}/adaptive/question", headers=s["headers"])
        r = client.post(f"/students/{s['id']}/adaptive/answer", json={"selected_answer": "1"}, headers=s["headers"])
        assert r.status_code == 200 and "coins_awarded" not in r.json() and "gems_awarded" not in r.json()
    db.expire_all()
    assert db.get(Wallet, sid) is None
    assert db.scalar(select(func.count(WalletTransaction.id)).where(WalletTransaction.student_id == sid)) == 0
