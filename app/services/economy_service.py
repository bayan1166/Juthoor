import uuid
from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.economy import Currency, InventoryItem, ShopItem, TxnReason, Wallet, WalletTransaction
from app.services.shop_catalog import ensure_shop_catalog

COINS_PER_CORRECT = 4
COINS_MASTERY_BONUS = 40
GEMS_MASTERY_BONUS = 1
COINS_STREAK_BONUS = 10
GEM_CONVERSION_RATE = 200


@dataclass
class RewardResult:
    coins: int
    gems: int


def get_or_create_wallet(db: Session, student_id: uuid.UUID) -> Wallet:
    wallet = db.get(Wallet, student_id)
    if wallet is None:
        wallet = Wallet(student_id=student_id, coins=50, gems=0)
        db.add(wallet)
        db.flush()
    return wallet


def apply_txn(db: Session, wallet: Wallet, currency: Currency, amount: int, reason: TxnReason, reference_id: str = "") -> None:
    if currency == Currency.coins:
        wallet.coins += amount
        if amount > 0:
            wallet.lifetime_coins_earned += amount
    else:
        wallet.gems += amount
        if amount > 0:
            wallet.lifetime_gems_earned += amount
    balance_after = wallet.coins if currency == Currency.coins else wallet.gems
    db.add(WalletTransaction(
        student_id=wallet.student_id, currency=currency, amount=amount,
        balance_after=balance_after, reason=reason, reference_id=reference_id,
    ))


def grant_reward(db: Session, student_id: uuid.UUID, is_correct: bool, action: str) -> RewardResult:
    wallet = get_or_create_wallet(db, student_id)
    coins = gems = 0
    if is_correct:
        coins += COINS_PER_CORRECT
        apply_txn(db, wallet, Currency.coins, COINS_PER_CORRECT, TxnReason.correct_answer)
    if action == "advance":
        coins += COINS_MASTERY_BONUS
        gems += GEMS_MASTERY_BONUS
        apply_txn(db, wallet, Currency.coins, COINS_MASTERY_BONUS, TxnReason.mastery_bonus)
        apply_txn(db, wallet, Currency.gems, GEMS_MASTERY_BONUS, TxnReason.mastery_bonus)
    return RewardResult(coins=coins, gems=gems)


def list_shop(db: Session, student_id: uuid.UUID, category: str | None = None) -> list[dict]:
    ensure_shop_catalog(db)
    query = select(ShopItem)
    if category:
        query = query.where(ShopItem.category == category)
    items = db.scalars(query).all()
    owned_ids = {i.item_id for i in db.scalars(select(InventoryItem).where(InventoryItem.student_id == student_id))}
    return [{
        "id": i.id, "category": i.category, "name": i.name, "gender": i.gender,
        "price_coins": i.price_coins, "price_gems": i.price_gems,
        "is_premium": i.is_premium, "owned": i.id in owned_ids or (i.price_coins == 0 and i.price_gems == 0),
    } for i in items]


def purchase_item(db: Session, student_id: uuid.UUID, item_id: str, currency: Currency) -> tuple[bool, str]:
    ensure_shop_catalog(db)
    item = db.get(ShopItem, item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "item_not_found")
    already_owned = db.scalar(select(InventoryItem).where(
        InventoryItem.student_id == student_id, InventoryItem.item_id == item_id))
    if already_owned:
        return False, "already_owned"

    price = item.price_gems if currency == Currency.gems else item.price_coins
    if currency == Currency.coins and item.is_premium and item.price_coins == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "premium_item_requires_gems")

    wallet = get_or_create_wallet(db, student_id)
    balance = wallet.gems if currency == Currency.gems else wallet.coins
    if balance < price:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "insufficient_balance")

    apply_txn(db, wallet, currency, -price, TxnReason.shop_purchase, reference_id=item_id)
    db.add(InventoryItem(student_id=student_id, item_id=item_id, currency_spent=currency, price_paid=price))
    db.commit()
    return True, "purchased"


def convert_coins_to_gems(db: Session, student_id: uuid.UUID, coins: int) -> Wallet:
    if coins <= 0 or coins % GEM_CONVERSION_RATE != 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"coins_must_be_multiple_of_{GEM_CONVERSION_RATE}")
    wallet = get_or_create_wallet(db, student_id)
    if wallet.coins < coins:
        raise HTTPException(status.HTTP_402_PAYMENT_REQUIRED, "insufficient_coins")
    gems = coins // GEM_CONVERSION_RATE
    apply_txn(db, wallet, Currency.coins, -coins, TxnReason.gem_conversion)
    apply_txn(db, wallet, Currency.gems, gems, TxnReason.gem_conversion)
    db.commit()
    return wallet


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
