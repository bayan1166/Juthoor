from app.engine import knowledge_graph as kg
from app.services.rag.embeddings import get_collection


def build_documents() -> tuple[list[str], list[str], list[dict]]:
    ids, docs, metas = [], [], []
    for skill_id, skill in kg.SKILLS.items():
        ids.append(f"{skill_id}::overview")
        docs.append(f"{skill.name_ar}. {skill.description}")
        metas.append({"skill_id": skill_id, "kind": "overview"})

        for i, step in enumerate(skill.ladder):
            ids.append(f"{skill_id}::ladder::{i}")
            docs.append(f"{skill.name_ar} - مستوى {i + 1}: {step}")
            metas.append({"skill_id": skill_id, "kind": "ladder", "level": i + 1})

        for i, err in enumerate(skill.typical_errors):
            ids.append(f"{skill_id}::error::{i}")
            docs.append(f"خطأ شائع في {skill.name_ar}: {err}")
            metas.append({"skill_id": skill_id, "kind": "misconception"})

        ids.append(f"{skill_id}::intervention")
        docs.append(f"طريقة علاجية لـ {skill.name_ar}: {skill.intervention}")
        metas.append({"skill_id": skill_id, "kind": "intervention"})
    return ids, docs, metas


def ingest_curriculum() -> int:
    collection = get_collection()
    ids, docs, metas = build_documents()
    collection.upsert(ids=ids, documents=docs, metadatas=metas)
    return len(ids)


if __name__ == "__main__":
    count = ingest_curriculum()
    print(f"ingested {count} chunks")
