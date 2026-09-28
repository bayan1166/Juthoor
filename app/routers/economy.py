import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_student_access
from app.models.economy import AvatarConfig
from app.models.org import User
from app.schemas.economy import (
    AvatarConfigIn, GemConversionRequest, PurchaseRequest, PurchaseResult, ShopItemOut, WalletOut,
)
from app.services import economy_service

router = APIRouter(prefix="/students/{student_id}/economy", tags=["economy"])


@router.get("/wallet", response_model=WalletOut)
def get_wallet(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    wallet = economy_service.get_or_create_wallet(db, student_id)
    db.commit()
    return wallet


@router.get("/shop", response_model=list[ShopItemOut])
def get_shop(student_id: uuid.UUID, category: str | None = None, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return economy_service.list_shop(db, student_id, category)


@router.post("/purchase", response_model=PurchaseResult)
def purchase(student_id: uuid.UUID, payload: PurchaseRequest, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    success, message = economy_service.purchase_item(db, student_id, payload.item_id, payload.currency)
    wallet = economy_service.get_or_create_wallet(db, student_id)
    return PurchaseResult(success=success, message=message, wallet=wallet)


@router.post("/convert", response_model=WalletOut)
def convert(student_id: uuid.UUID, payload: GemConversionRequest, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return economy_service.convert_coins_to_gems(db, student_id, payload.coins)


@router.put("/avatar")
def set_avatar(student_id: uuid.UUID, payload: AvatarConfigIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    row = db.get(AvatarConfig, student_id) or AvatarConfig(student_id=student_id)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.add(row)
    db.commit()
    return {"status": "saved"}
