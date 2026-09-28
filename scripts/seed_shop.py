import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.engine import avatar_items as ai
from app.models.economy import ShopItem

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


def main():
    db = SessionLocal()
    try:
        count = 0
        for item in ai.CATALOG:
            existing = db.get(ShopItem, item.id)
            row = to_shop_item(item)
            if existing is None:
                db.add(row)
            else:
                for field in ("category", "name", "gender", "price_coins", "price_gems", "is_premium"):
                    setattr(existing, field, getattr(row, field))
            count += 1
        db.commit()
        print(f"seeded {count} shop items")
    finally:
        db.close()


if __name__ == "__main__":
    main()
