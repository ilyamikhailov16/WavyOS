import subprocess

from scripts import script_runner as module


def test_run_script_rejects_non_python_files(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    module.run_script("not_python.txt")

    assert calls == []


def test_run_script_rejects_missing_file(tmp_path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: calls.append((args, kwargs)))

    module.run_script("missing.py", script_path=tmp_path)

    assert calls == []


def test_run_script_builds_expected_command(tmp_path, monkeypatch) -> None:
    script_path = tmp_path / "demo.py"
    script_path.write_text("print('ok')", encoding="utf-8")
    commands = []

    class Result:
        returncode = 0

    def fake_run(cmd, check):
        commands.append((cmd, check))
        return Result()

    monkeypatch.setattr(module.subprocess, "run", fake_run)

    module.run_script("demo.py", tmp_path, "arg1", mode="fast")

    assert commands == [
        ([module.sys.executable, str(script_path), "arg1", "--mode=fast"], True)
    ]
