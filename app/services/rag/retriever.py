from functools import lru_cache

from app.config import settings
from app.services import curriculum_map as cur
from app.services.rag.textutil import tokens


@lru_cache(maxsize=1)
def _corpus() -> list[dict]:
    out = []
    for unit, lesson in cur.all_lessons():
        key = cur.lesson_key(unit, lesson)
        for index, concept in enumerate(cur.concepts_for(key)):
            text = f"{concept.title}: {cur.plain(concept.text)}"
            out.append({
                "id": f"{key}:{index}",
                "text": text,
                "metadata": {"skill_id": lesson.skill or "", "lesson": key},
                "tokens": set(tokens(text)),
            })
    return out


def _lexical(query: str, skill_id: str | None, top_k: int) -> list[dict]:
    wanted = set(tokens(query))
    pool = [c for c in _corpus() if not skill_id or c["metadata"]["skill_id"] == skill_id] or _corpus()
    ranked = sorted(pool, key=lambda c: len(wanted & c["tokens"]), reverse=True)
    return [
        {"id": c["id"], "text": c["text"], "metadata": c["metadata"], "distance": 0.0}
        for c in ranked[:top_k]
    ]


def _vector(query: str, skill_id: str | None, top_k: int) -> list[dict]:
    from app.services.rag.embeddings import get_collection

    collection = get_collection()
    where = {"skill_id": skill_id} if skill_id else None
    result = collection.query(query_texts=[query], n_results=top_k, where=where)
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    return [
        {"id": cid, "text": doc, "metadata": meta, "distance": dist}
        for cid, doc, meta, dist in zip(ids, docs, metas, dists)
    ]


def retrieve(query: str, skill_id: str | None = None, top_k: int = 5) -> list[dict]:
    if settings.enable_vector_store:
        try:
            return _vector(query, skill_id, top_k)
        except Exception:
            pass
    return _lexical(query, skill_id, top_k)
