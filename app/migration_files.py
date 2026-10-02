"""Discovery and validation of migration files (pure; no database driver needed)."""
from __future__ import annotations

import re
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parents[1] / "migrations" / "versions"
LOCK_KEY = 727_274_001
_NAME = re.compile(r"^(\d{4})_[a-z0-9_]+\.sql$")


def discover(directory: Path = MIGRATIONS_DIR) -> list[tuple[str, Path]]:
    """Ordered ``(version, path)`` pairs; raises on a malformed name, a duplicate or a gap."""
    found: list[tuple[str, Path]] = []
    for path in sorted(directory.glob("*.sql")):
        match = _NAME.match(path.name)
        if not match:
            raise ValueError(f"migration file name must look like 0001_name.sql: {path.name}")
        found.append((match.group(1), path))
    versions = [v for v, _ in found]
    if len(set(versions)) != len(versions):
        raise ValueError("duplicate migration version numbers")
    if versions != [f"{i:04d}" for i in range(1, len(versions) + 1)]:
        raise ValueError(f"migration versions must be consecutive from 0001, got {versions}")
    for _v, path in found:
        if "%" in path.read_text(encoding="utf-8"):
            raise ValueError(f"{path.name}: percent sign not allowed")
    return found
