def risk_level(tree_health: float, answered: int, days_since_active, gap_count: int) -> str:
    if answered == 0:
        return "inactive"
    stale = days_since_active is not None
    if gap_count > 0 or tree_health < 0.25 or (stale and days_since_active > 7):
        return "high"
    if tree_health < 0.5 or (stale and days_since_active > 3):
        return "medium"
    return "low"


def rank_rows(rows: list[dict]) -> list[dict]:
    ordered = sorted(rows, key=lambda r: (-r["score"], r["duration_seconds"], r["full_name"]))
    out = []
    last_key = None
    last_rank = 0
    for index, row in enumerate(ordered, start=1):
        key = (row["score"], round(row["duration_seconds"], 3))
        rank = last_rank if key == last_key else index
        out.append({**row, "rank": rank})
        last_key, last_rank = key, rank
    return out
