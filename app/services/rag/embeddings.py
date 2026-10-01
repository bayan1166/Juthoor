from app.config import settings

_client = None
_collection = None


def get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection
    import chromadb
    from chromadb.utils import embedding_functions

    _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    _collection = _client.get_or_create_collection(
        name=settings.chroma_collection,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection
