import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_self, require_student_access
from app.engine import avatar as av
from app.engine import avatar_items as ai
from app.models.economy import AvatarConfig
from app.models.org import User
from app.schemas.economy import (
    AvatarConfigIn, GemConversionRequest, PurchaseRequest, PurchaseResult, ShopItemOut, WalletOut,
)
from app.services import avatar_render, economy_service

router = APIRouter(prefix="/students/{student_id}/economy", tags=["economy"])


def _row(db: Session, student_id: uuid.UUID) -> AvatarConfig:
    row = db.get(AvatarConfig, student_id)
    if row is None:
        row = AvatarConfig(student_id=student_id)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


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


@router.get("/catalog")
def get_catalog(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    meta = {item.id: item for item in ai.CATALOG}
    out = []
    for row in economy_service.list_shop(db, student_id, None):
        item = meta.get(row["id"])
        if item is None:
            continue
        out.append({**row, "group": item.group, "bundle": [list(pair) for pair in item.bundle]})
    return out


@router.get("/options")
def get_options(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return {
        "skins": [{"id": sid, "name": name} for sid, name in av.SKIN_OPTIONS],
        "hair_styles": [{"id": k, "name": v[0], "gender": v[1]} for k, v in av.HAIR_STYLES.items()],
        "hair_colors": [{"id": k, "name": v[0], "hex": v[1]} for k, v in av.HAIR_COLORS.items()],
    }


@router.get("/previews")
def get_previews(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    base = avatar_render.config_dict(_row(db, student_id))
    out = {}

    def add(key: str, cfg: dict) -> None:
        uid = "p" + key.replace(":", "_")
        out[key] = {"svg": avatar_render.render(cfg, uid), "uid": uid}

    for item in ai.CATALOG:
        if item.gender not in (None, base["gender"]):
            continue
        cfg = {**base, item.cat: item.id}
        for cat, item_id in item.bundle:
            cfg[cat] = item_id
        add("i:" + item.id, cfg)
    for sid, _ in av.SKIN_OPTIONS:
        add("skin:" + sid, {**base, "skin": sid})
    for key, value in av.HAIR_STYLES.items():
        if value[1] in (None, base["gender"]):
            add("hair:" + key, {**base, "hair": key})
    for key in av.HAIR_COLORS:
        add("hc:" + key, {**base, "hair_color": key})
    return out


@router.post("/purchase", response_model=PurchaseResult)
def purchase(student_id: uuid.UUID, payload: PurchaseRequest, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    require_self(student_id, user)
    success, message = economy_service.purchase_item(db, student_id, payload.item_id, payload.currency)
    wallet = economy_service.get_or_create_wallet(db, student_id)
    return PurchaseResult(success=success, message=message, wallet=wallet)


@router.post("/convert", response_model=WalletOut)
def convert(student_id: uuid.UUID, payload: GemConversionRequest, db: Session = Depends(get_db),
            user: User = Depends(get_current_user)):
    require_self(student_id, user)
    return economy_service.convert_coins_to_gems(db, student_id, payload.coins)


@router.put("/avatar")
def set_avatar(student_id: uuid.UUID, payload: AvatarConfigIn, db: Session = Depends(get_db),
               user: User = Depends(get_current_user)):
    require_self(student_id, user)
    data = payload.model_dump()
    bad = economy_service.unowned_avatar_items(db, student_id, data)
    if bad:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "item_not_owned:" + ",".join(bad))
    row = _row(db, student_id)
    for key, value in data.items():
        setattr(row, key, value)
    db.add(row)
    db.commit()
    return {"status": "saved", "svg": avatar_render.render(row, "me")}


@router.get("/avatar", response_model=AvatarConfigIn)
def get_avatar(student_id: uuid.UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_student_access(student_id, user, db)
    return AvatarConfigIn(**avatar_render.config_dict(_row(db, student_id)))
