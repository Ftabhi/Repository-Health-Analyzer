"""Minimal app entrypoint for GitHub Repository Health Analyzer."""
import subprocess
import sys
from pathlib import Path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(project_root / "dashboard" / "app.py")],
        cwd=str(project_root),
        check=True,
    )


if __name__ == "__main__":
    main()
