import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.shop_catalog import PREMIUM_GROUPS, clean_name, sync_shop_catalog, to_shop_item  # noqa: F401


def main():
    db = SessionLocal()
    try:
        print(f"seeded {sync_shop_catalog(db)} shop items")
    finally:
        db.close()


if __name__ == "__main__":
    main()
