"""Check that the Python environment can run Juthoor (exit 0) or say exactly what to install (exit 4).

    python scripts/check_env.py          # runtime dependencies
    python scripts/check_env.py --dev    # + test dependencies
"""
import argparse
import importlib
import sys

RUNTIME = [
    ("fastapi", "fastapi"), ("uvicorn", "uvicorn[standard]"), ("sqlalchemy", "sqlalchemy"),
    ("psycopg2", "psycopg2-binary"), ("pydantic", "pydantic"), ("pydantic_settings", "pydantic-settings"),
    ("email_validator", "email-validator"), ("multipart", "python-multipart"), ("jwt", "PyJWT"),
    ("bcrypt", "bcrypt"), ("networkx", "networkx"),
]
DEV = [("pytest", "pytest"), ("httpx", "httpx")]


def missing(modules):
    out = []
    for module, package in modules:
        try:
            importlib.import_module(module)
        except Exception as exc:  # ImportError, or a broken install raising something else
            out.append((package, f"{type(exc).__name__}: {exc}"))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print(f"Python {sys.version.split()[0]} is too old: Juthoor needs Python 3.11 or newer.")
        return 4
    problems = missing(RUNTIME + (DEV if args.dev else []))
    if problems:
        target = "requirements-dev.txt" if args.dev else "requirements.txt"
        print("Missing or broken Python packages:")
        for package, why in problems:
            print(f"  - {package}  ({why})")
        print(f"Fix: {sys.executable} -m pip install -r {target}")
        return 4
    print(f"python {sys.version.split()[0]}: all {'runtime + test' if args.dev else 'runtime'} dependencies import correctly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
