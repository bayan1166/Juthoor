from functools import lru_cache

from app.engine import avatar as av

FIELDS = ("gender", "skin", "clothing", "accessories", "top", "hair", "hair_color", "neck")


@lru_cache(maxsize=4096)
def _render(gender, skin, clothing, accessories, top, hair, hair_color, neck, uid):
    return av.avatar_svg(gender=gender, skin=skin, clothing=clothing, accessories=accessories,
                         top=top, hair=hair, hair_color=hair_color, neck=neck, uid=uid)


def _field(cfg, key):
    if isinstance(cfg, dict):
        return cfg[key]
    return getattr(cfg, key)


def render(cfg, uid: str) -> str:
    return _render(*(_field(cfg, k) for k in FIELDS), uid)


def config_dict(cfg) -> dict:
    return {k: _field(cfg, k) for k in FIELDS}


def svgs_for(db, users) -> dict:
    from sqlalchemy import select

    from app.models.economy import AvatarConfig
    from app.models.org import UserRole

    by_id = {u.id: u for u in users if u.role == UserRole.student}
    if not by_id:
        return {}
    out = {}
    for row in db.scalars(select(AvatarConfig).where(AvatarConfig.student_id.in_(list(by_id)))):
        user = by_id[row.student_id]
        out[row.student_id] = render(row, f"a{user.handle or str(user.id)[:8]}")
    return out
