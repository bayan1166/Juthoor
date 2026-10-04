"""Avatar item ownership.

Coins, gems, the wallet and the avatar shop are no longer part of the product: nothing awards, spends or shows
them. Their tables (wallets, wallet_transactions, shop_items, inventory_items) are kept untouched so existing
databases and the migration history stay valid. The avatar item catalogue still says which outfits are free; an
item that used to cost coins or gems can be worn only if the learner already owned it.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.economy import InventoryItem, ShopItem
from app.services.shop_catalog import ensure_shop_catalog

AVATAR_ITEM_FIELDS = ("clothing", "top", "neck", "accessories")


def unowned_avatar_items(db: Session, student_id: uuid.UUID, config: dict) -> list[str]:
    from app.engine import avatar_items as ai
    ensure_shop_catalog(db)
    owned = {i.item_id for i in db.scalars(select(InventoryItem).where(InventoryItem.student_id == student_id))}
    bundled = {iid for it in ai.CATALOG if it.id in owned for _, iid in it.bundle}
    bad = []
    for field_name in AVATAR_ITEM_FIELDS:
        value = config.get(field_name)
        item = db.get(ShopItem, value) if value else None
        if item is None:
            continue
        if item.price_coins == 0 and item.price_gems == 0:
            continue
        if value in owned or value in bundled:
            continue
        bad.append(value)
    return bad
