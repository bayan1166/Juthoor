import uuid

from pydantic import BaseModel, Field

from app.models.economy import Currency


class WalletOut(BaseModel):
    student_id: uuid.UUID
    coins: int
    gems: int
    lifetime_coins_earned: int
    lifetime_gems_earned: int


class ShopItemOut(BaseModel):
    id: str
    category: str
    name: str
    gender: str | None
    price_coins: int
    price_gems: int
    is_premium: bool
    owned: bool


class PurchaseRequest(BaseModel):
    item_id: str
    currency: Currency


class PurchaseResult(BaseModel):
    success: bool
    message: str
    wallet: WalletOut


class GemConversionRequest(BaseModel):
    coins: int


class AvatarConfigIn(BaseModel):
    gender: str = Field(max_length=10)
    skin: str = Field(max_length=20)
    clothing: str = Field(max_length=40)
    top: str = Field(max_length=40)
    neck: str = Field(max_length=40)
    accessories: str = Field(max_length=40)
    hair: str = Field(max_length=20)
    hair_color: str = Field(max_length=20)
