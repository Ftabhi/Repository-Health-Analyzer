import subprocess
import sys

import app as app_module


def test_main_invokes_streamlit_dashboard(monkeypatch):
    calls = []

    def fake_run(command, check=False, cwd=None):
        calls.append((command, check, cwd))
        return None

    monkeypatch.setattr(app_module.subprocess, "run", fake_run)
    app_module.main()

    assert calls
    command, check, cwd = calls[0]
    assert command[:4] == [sys.executable, "-m", "streamlit", "run"]
    assert any("dashboard" in part and "app.py" in part for part in command)
    assert check is True
    assert cwd is not None
