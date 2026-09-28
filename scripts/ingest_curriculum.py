import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.rag.ingest import ingest_curriculum

if __name__ == "__main__":
    count = ingest_curriculum()
    print(f"ingested {count} curriculum chunks into chroma")
