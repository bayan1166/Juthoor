import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models  # noqa: F401 (registers every model on Base.metadata)
from app.database import ensure_schema


def main():
    added = ensure_schema()
    print("tables created" + (f"; upgraded columns: {', '.join(added)}" if added else ""))


if __name__ == "__main__":
    main()
