import argparse
import os
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SQLITE_FILE = ROOT / "juthoor_demo.db"


def has_database_url() -> bool:
    if os.environ.get("DATABASE_URL"):
        return True
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("DATABASE_URL=") and line.split("=", 1)[1].strip():
                return True
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()

    env = dict(os.environ)
    env.setdefault("DEMO_MODE", "1")
    env.setdefault("JUDGE_MODE", "0" if args.full else "1")
    env.setdefault("PUBLIC_URL", f"http://localhost:{args.port}")
    if not has_database_url():
        env["DATABASE_URL"] = f"sqlite:///{SQLITE_FILE.as_posix()}"
        if args.reset and SQLITE_FILE.exists():
            SQLITE_FILE.unlink()

    python = sys.executable
    steps = ["scripts/init_db.py", "scripts/seed_shop.py", "scripts/seed_demo.py"]
    if args.reset:
        print("RESET: every table in the configured database will be wiped and recreated.")
        steps.insert(0, "scripts/reset_db.py")
    for script in steps:
        subprocess.run([python, script], cwd=ROOT, env=env, check=True)

    url = f"http://localhost:{args.port}/app/"
    print(f"Juthoor is running at {url}")
    print("Demo accounts use the password demo1234 (teacher@demo.jo, parent@demo.jo, student1@demo.jo ...)")
    if not args.no_browser:
        threading.Thread(target=lambda: (time.sleep(2.0), webbrowser.open(url)), daemon=True).start()
    try:
        subprocess.run([python, "-m", "uvicorn", "app.main:app", "--port", str(args.port)], cwd=ROOT, env=env)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
