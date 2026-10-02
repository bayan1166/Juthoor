"""The avatar shop catalogue: code (app/engine/avatar_items.CATALOG) is the source of truth, the
`shop_items` table is its persisted copy (prices, ownership joins).

`ensure_shop_catalog` inserts any catalogue item missing from the table. It runs before every read
or check that depends on shop rows, so a freshly initialised database (or a truncated test database)
never shows an empty shop and — more importantly — the "do you own this item?" check can never be
bypassed because a row is missing.
"""
from __future__ import annotations

import logging
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.engine import avatar_items as ai
from app.models.economy import ShopItem

logger = logging.getLogger("juthoor.shop")

PREMIUM_GROUPS = {"jobs", "heritage", "jobcaps"}
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002600-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U0000FE00-\U0000FE0F"
    "\U0000200D"
    "\U00002190-\U000021FF"
    "\U00002B00-\U00002BFF"
    "]+",
    flags=re.UNICODE,
)


def clean_name(name: str) -> str:
    stripped = EMOJI_PATTERN.sub("", name)
    return re.sub(r"\s+", " ", stripped).strip()


def to_shop_item(item: ai.Item) -> ShopItem:
    is_premium = item.group in PREMIUM_GROUPS
    price_coins = 0 if is_premium else item.price * 4
    price_gems = max(1, item.price // 15) if is_premium else 0
    return ShopItem(
        id=item.id,
        category=item.cat,
        name=clean_name(item.name),
        gender=item.gender,
        price_coins=price_coins,
        price_gems=price_gems,
        is_premium=is_premium,
        bundle_of=None,
    )


def ensure_shop_catalog(db: Session) -> int:
    """Insert catalogue items missing from shop_items. Returns how many were added."""
    present = set(db.scalars(select(ShopItem.id)))
    missing = [item for item in ai.CATALOG if item.id not in present]
    if not missing:
        return 0
    for item in missing:
        db.add(to_shop_item(item))
    try:
        db.commit()
    except IntegrityError:
        # Another request inserted the same rows first; theirs are identical.
        db.rollback()
        return 0
    logger.info("shop catalogue: added %d missing items", len(missing))
    return len(missing)


def sync_shop_catalog(db: Session) -> int:
    """Insert missing items and refresh name/price fields of existing ones (used by seed_shop)."""
    count = 0
    for item in ai.CATALOG:
        row = to_shop_item(item)
        existing = db.get(ShopItem, item.id)
        if existing is None:
            db.add(row)
        else:
            for field in ("category", "name", "gender", "price_coins", "price_gems", "is_premium"):
                setattr(existing, field, getattr(row, field))
        count += 1
    db.commit()
    return count
