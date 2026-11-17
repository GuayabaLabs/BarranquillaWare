"""El arranque elige el entorno local sin alterar imports ni reiniciarse en bucle."""
import os
from pathlib import Path

import main


def test_startup_prefers_project_environment(tmp_path, monkeypatch):
    executable = tmp_path / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(main.sys, "prefix", str(tmp_path / "global"))
    monkeypatch.setattr(main.sys, "argv", ["main.py", "--example"])
    calls = []
    monkeypatch.setattr(main.os, "execv", lambda path, args: calls.append((path, args)))
    main._prefer_project_python()
    assert calls == [(str(executable), [str(executable), str(tmp_path / "main.py"), "--example"])]


def test_startup_does_not_restart_inside_project_environment(tmp_path, monkeypatch):
    executable = tmp_path / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    executable.parent.mkdir(parents=True)
    executable.touch()
    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(main.sys, "prefix", str(tmp_path / ".venv"))
    monkeypatch.setattr(main.os, "execv", lambda *args: (_ for _ in ()).throw(AssertionError("reinicio inesperado")))
    main._prefer_project_python()


def test_startup_without_environment_keeps_current_python(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "__file__", str(tmp_path / "main.py"))
    monkeypatch.setattr(main.os, "execv", lambda *args: (_ for _ in ()).throw(AssertionError("reinicio inesperado")))
    main._prefer_project_python()
