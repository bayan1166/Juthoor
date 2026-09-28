from app.services.rag.embeddings import get_collection


def retrieve(query: str, skill_id: str | None = None, top_k: int = 5) -> list[dict]:
    collection = get_collection()
    where = {"skill_id": skill_id} if skill_id else None
    result = collection.query(query_texts=[query], n_results=top_k, where=where)
    chunks = []
    ids = result.get("ids", [[]])[0]
    docs = result.get("documents", [[]])[0]
    metas = result.get("metadatas", [[]])[0]
    dists = result.get("distances", [[]])[0]
    for cid, doc, meta, dist in zip(ids, docs, metas, dists):
        chunks.append({"id": cid, "text": doc, "metadata": meta, "distance": dist})
    return chunks
