"""Avatar configuration, plus the legacy coin/gem economy tables.

Coins, gems, the wallet and the avatar shop were removed from the product. Wallet, WalletTransaction, ShopItem
and InventoryItem stay defined only so existing databases (and their history) remain valid; the application no
longer writes coins or gems anywhere. ShopItem/InventoryItem still tell which avatar outfits a learner may wear.
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Currency(str, enum.Enum):
    coins = "coins"
    gems = "gems"


class TxnReason(str, enum.Enum):
    correct_answer = "correct_answer"
    streak_bonus = "streak_bonus"
    mastery_bonus = "mastery_bonus"
    challenge_reward = "challenge_reward"
    season_reward = "season_reward"
    shop_purchase = "shop_purchase"
    gem_conversion = "gem_conversion"
    admin_grant = "admin_grant"
    real_money_purchase = "real_money_purchase"


class Wallet(Base):
    __tablename__ = "wallets"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    coins: Mapped[int] = mapped_column(Integer, default=0)
    gems: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_coins_earned: Mapped[int] = mapped_column(Integer, default=0)
    lifetime_gems_earned: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    currency: Mapped[Currency] = mapped_column(Enum(Currency))
    amount: Mapped[int] = mapped_column(Integer)
    balance_after: Mapped[int] = mapped_column(Integer)
    reason: Mapped[TxnReason] = mapped_column(Enum(TxnReason))
    reference_id: Mapped[str] = mapped_column(String(80), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)


class ShopItem(Base):
    __tablename__ = "shop_items"

    id: Mapped[str] = mapped_column(String(60), primary_key=True)
    category: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120))
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    price_coins: Mapped[int] = mapped_column(Integer, default=0)
    price_gems: Mapped[int] = mapped_column(Integer, default=0)
    is_premium: Mapped[bool] = mapped_column(default=False)
    bundle_of: Mapped[str | None] = mapped_column(String(60), nullable=True)
    season_exclusive: Mapped[bool] = mapped_column(default=False)


class InventoryItem(Base):
    __tablename__ = "inventory_items"
    __table_args__ = (UniqueConstraint("student_id", "item_id", name="uq_student_item"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("shop_items.id"))
    currency_spent: Mapped[Currency] = mapped_column(Enum(Currency))
    price_paid: Mapped[int] = mapped_column(Integer)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AvatarConfig(Base):
    __tablename__ = "avatar_configs"

    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    gender: Mapped[str] = mapped_column(String(10), default="ولد")
    skin: Mapped[str] = mapped_column(String(20), default="f8d25c")
    clothing: Mapped[str] = mapped_column(String(40), default="shirtCrewNeck")
    top: Mapped[str] = mapped_column(String(40), default="none")
    neck: Mapped[str] = mapped_column(String(40), default="none")
    accessories: Mapped[str] = mapped_column(String(40), default="blank")
    hair: Mapped[str] = mapped_column(String(20), default="straight")
    hair_color: Mapped[str] = mapped_column(String(20), default="black")
