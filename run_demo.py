"""Start the whole MVP with one command (Windows / macOS / Linux):

    python run_demo.py            # API on :8000, UI on :8501
    python run_demo.py --reset    # delete the local SQLite demo database first

Uses DATABASE_URL from .env if set; otherwise a local SQLite file (no Docker needed).
Creates tables, seeds the shop and the demo accounts (safe to re-run), then launches
uvicorn and Streamlit. Press Ctrl+C to stop both.
"""
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SQLITE_FILE = ROOT / "juthoor_demo.db"


def _env_has_database_url() -> bool:
    if os.environ.get("DATABASE_URL"):
        return True
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL=") and line.split("=", 1)[1].strip():
                return True
    return False


def main():
    env = dict(os.environ)
    if not _env_has_database_url():
        env["DATABASE_URL"] = f"sqlite:///{SQLITE_FILE.as_posix()}"
        if "--reset" in sys.argv and SQLITE_FILE.exists():
            SQLITE_FILE.unlink()
        print(f"[juthoor] using SQLite: {SQLITE_FILE}")
    env.setdefault("JUTHOOR_API_URL", "http://localhost:8000")

    py = sys.executable
    for script in ("scripts/init_db.py", "scripts/seed_shop.py", "scripts/seed_demo.py"):
        print(f"[juthoor] {script}")
        subprocess.run([py, script], cwd=ROOT, env=env, check=True)

    api = subprocess.Popen([py, "-m", "uvicorn", "app.main:app", "--port", "8000"], cwd=ROOT, env=env)
    time.sleep(2)
    ui = subprocess.Popen([py, "-m", "streamlit", "run", "web/streamlit_app.py", "--server.port", "8501"],
                          cwd=ROOT, env=env)
    print("[juthoor] API  http://localhost:8000/docs")
    print("[juthoor] UI   http://localhost:8501   (password for demo accounts: demo1234)")
    try:
        while api.poll() is None and ui.poll() is None:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for proc in (ui, api):
            if proc.poll() is None:
                proc.terminate()


if __name__ == "__main__":
    main()
