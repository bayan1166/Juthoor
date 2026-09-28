import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: F401
from app.database import Base, engine


def main():
    Base.metadata.create_all(bind=engine)
    print("tables created")


if __name__ == "__main__":
    main()
