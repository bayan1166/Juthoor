import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text

from app import models as _models
from app.database import Base, engine, ensure_schema


def main():
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("DROP SCHEMA public CASCADE"))
            conn.execute(text("CREATE SCHEMA public"))
        else:
            Base.metadata.drop_all(bind=conn)
    ensure_schema()
    print("database reset: all tables recreated")


if __name__ == "__main__":
    main()
