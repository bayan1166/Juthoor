"""Issue or rotate an organization's join code (prints the plain code once).

    python scripts/org_join_code.py <organization-slug>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models.org import Organization  # noqa: E402
from app.services import org_access  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    with SessionLocal() as db:
        org = db.scalar(select(Organization).where(Organization.slug == argv[1]))
        if org is None:
            print(f"no organization with slug {argv[1]!r}")
            return 1
        code = org_access.issue_join_code(org)
        db.commit()
    print(f"join code for {argv[1]}: {code}\nShare it only with the school's teachers and students; running this again rotates it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
