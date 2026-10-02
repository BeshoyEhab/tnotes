# tests/test_actions.py
from tnotes import actions

def test_find_exe_order(monkeypatch):
    monkeypatch.setattr(actions.shutil, "which", lambda n: "/usr/bin/" + n if n == "wl-copy" else None)
    assert actions.find_exe(["wl-copy", "xclip", "xsel"]) == "/usr/bin/wl-copy"
    monkeypatch.setattr(actions.shutil, "which", lambda n: None)
    assert actions.find_exe(["wl-copy", "xclip"]) is None

def test_run_command_requires_confirm(capsys):
    rc = actions.run_command("exit 3", confirm=False)
    assert rc == 3

def test_run_command_confirm_no(monkeypatch, capsys):
    monkeypatch.setattr("builtins.input", lambda _: "n")
    rc = actions.run_command("echo SHOULD-NOT-RUN", confirm=True)
    assert rc == 130
    assert "SHOULD-NOT-RUN" not in capsys.readouterr().out

def test_open_target_quiet_detaches_stdio(monkeypatch):
    calls = {}
    class FakeProc:
        returncode = 0
    def fake_run(argv, **kwargs):
        calls.update(kwargs)
        return FakeProc()
    monkeypatch.setattr(actions, "find_exe", lambda names: "/usr/bin/xdg-open")
    monkeypatch.setattr(actions.subprocess, "run", fake_run)
    assert actions.open_target("https://x.example", quiet=True) == 0
    import subprocess
    assert calls.get("stdout") == subprocess.DEVNULL
    assert calls.get("stderr") == subprocess.DEVNULL
    calls.clear()
    assert actions.open_target("https://x.example") == 0
    assert calls.get("stdout") is None
    assert calls.get("stderr") is None
