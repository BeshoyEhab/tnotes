# tests/test_picker.py
from tnotes.picker import format_row, build_rows
from tnotes import store
from tnotes.cli import main

def test_format_row_icons_scope():
    assert format_row({"type": "url", "title": "t", "tags": ["a"], "scope": "global", "status": "active"}).startswith("🔗 t [a] G")
    assert format_row({"type": "cmd", "title": "t", "tags": [], "scope": "local", "status": "active"}).startswith("$ t ·")
    assert "✔" in format_row({"type": "note", "title": "t", "tags": [], "scope": "local", "status": "done"})

def test_build_rows_tab_id():
    rows = build_rows([{"id": "abc123", "type": "note", "title": "hi", "tags": [], "scope": "global", "status": "active"}])
    assert rows[0].endswith("\tabc123")

def test_open_second_action(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="n", body="see https://a.example and https://b.example",
                        tags=[], scope="global", cwd=None, show_on_open=True)
    monkeypatch.setattr("tnotes.cli_actions.actions.open_target", lambda url: (print(url), 0)[1])
    assert main(["open", e["id"], "2"]) == 0
    assert "https://b.example" in capsys.readouterr().out

class _FakeProc:
    def __init__(self, out: bytes, rc: int = 0):
        self.stdout = out
        self.returncode = rc

def _patch_fzf(monkeypatch, out: bytes, rc: int = 0):
    from tnotes import picker as P
    seen = {}
    def fake_run(argv, input=None, capture_output=False, **kw):
        seen["argv"] = argv
        return _FakeProc(out, rc)
    monkeypatch.setattr(P.subprocess, "run", fake_run)
    return seen

def test_run_picker_ctrl_n_returns_query(monkeypatch):
    from tnotes import picker as P
    seen = _patch_fzf(monkeypatch, b"buy milk\nctrl-n\n")
    rows = [{"id": "a1b2c3", "type": "note", "title": "x", "tags": [], "scope": "global", "status": "active"}]
    assert P.run_picker(rows) == ("ctrl-n", "buy milk")
    exp = next(a for a in seen["argv"] if a.startswith("--expect="))
    assert "ctrl-n" in exp
    assert "--print-query" in seen["argv"]

def test_picker_header_bar_colored_keys(monkeypatch):
    from tnotes import picker as P
    bar = P.header_bar()
    assert "ctrl-n" in bar and "\033[" in bar
    seen = _patch_fzf(monkeypatch, b"\nq\nnope\tx\n")
    P.run_picker([{"id": "x", "type": "note", "title": "t", "tags": [], "scope": "global", "status": "active"}])
    assert "--header" in seen["argv"] and bar in seen["argv"]
    assert "--ansi" in seen["argv"]

def test_run_picker_abort_rc130(monkeypatch):
    from tnotes import picker as P
    _patch_fzf(monkeypatch, b"half-typed\n", rc=130)
    rows = [{"id": "a1b2c3", "type": "note", "title": "x", "tags": [], "scope": "global", "status": "active"}]
    assert P.run_picker(rows) == (None, None)

def test_run_picker_enter_no_match_is_noop(monkeypatch):
    from tnotes import picker as P
    _patch_fzf(monkeypatch, b"nomatch\n\n")
    rows = [{"id": "a1b2c3", "type": "note", "title": "x", "tags": [], "scope": "global", "status": "active"}]
    assert P.run_picker(rows) == (None, None)

def test_run_picker_select_with_query(monkeypatch):
    from tnotes import picker as P
    seen = _patch_fzf(monkeypatch, b"mil\n\n\xf0\x9f\x93\x9d milk \xc2\xb7\ta1b2c3\n")
    rows = [{"id": "a1b2c3", "type": "note", "title": "milk", "tags": [], "scope": "local", "status": "active"}]
    assert P.run_picker(rows) == ("enter", "a1b2c3")
