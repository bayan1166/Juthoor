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
DEFAULT_DATABASE_URL = "postgresql://postgres:1234@localhost:5432/Juthoor"


def dotenv_value(key: str) -> str:
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def has_database_url() -> bool:
    return bool(os.environ.get("DATABASE_URL") or dotenv_value("DATABASE_URL"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--sqlite", action="store_true",
                        help="offline fallback only: use a local SQLite file instead of PostgreSQL")
    args = parser.parse_args()

    env = dict(os.environ)
    if not env.get("DEMO_MODE", "").strip():
        env["DEMO_MODE"] = "1"
    if not env.get("JUDGE_MODE", "").strip():
        env["JUDGE_MODE"] = "0" if args.full else "1"
    env.setdefault("PUBLIC_URL", f"http://localhost:{args.port}")
    sys.path.insert(0, str(ROOT))
    from app.services.secrets_check import suggestion, weak_secret_reason
    if weak_secret_reason(env.get("JWT_SECRET") or dotenv_value("JWT_SECRET")):
        # Demo only: a random per-run secret instead of the .env placeholder (sessions reset on restart).
        env["JWT_SECRET"] = suggestion()
        print("demo: JWT_SECRET in .env is a placeholder, using a random secret for this run")
    if args.sqlite:
        # Explicit opt-in only. PostgreSQL is the supported and judged configuration.
        env["DATABASE_URL"] = f"sqlite:///{SQLITE_FILE.as_posix()}"
        if args.reset and SQLITE_FILE.exists():
            SQLITE_FILE.unlink()
    elif not has_database_url():
        env["DATABASE_URL"] = DEFAULT_DATABASE_URL

    python = sys.executable
    deps = subprocess.run([python, "scripts/check_env.py"], cwd=ROOT, env=env)
    if deps.returncode != 0:
        sys.exit(deps.returncode)
    check = subprocess.run([python, "scripts/check_db.py"], cwd=ROOT, env=env)
    if check.returncode != 0:
        sys.exit(check.returncode)
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
