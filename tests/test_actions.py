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
