# tests/test_picker.py
from tnotes.models import Entry
from tnotes.picker import format_row, build_rows
from tnotes import store
from tnotes.cli import main

def _entry(**kw):
    base = {"id": "a1b2c3", "type": "note", "title": "t", "tags": [],
            "scope": "local", "cwd": None, "status": "active",
            "show_on_open": True, "body": "b", "created": "t", "updated": "t"}
    base.update(kw)
    return Entry(**base)

def test_format_row_icons_scope():
    assert format_row(_entry(type="url", title="t", tags=["a"], scope="global", status="active")).startswith("↗ t #a G")
    assert format_row(_entry(type="cmd", title="t", tags=[], scope="local", status="active")).startswith("❯ t ·")
    assert "✔" in format_row(_entry(type="note", title="t", tags=[], scope="local", status="done"))

def test_build_rows_tab_id():
    rows = build_rows([_entry(id="abc123", type="note", title="hi", tags=[], scope="global", status="active")])
    assert rows[0].endswith("\tabc123")

def test_open_second_action(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="n", body="see https://a.example and https://b.example",
                        tags=[], scope="global", cwd=None, show_on_open=True)
    monkeypatch.setattr("tnotes.cli_actions.actions.open_target", lambda url: (print(url), 0)[1])
    assert main(["open", e.id, "2"]) == 0
    assert "https://b.example" in capsys.readouterr().out

class _FakeProc:
    def __init__(self, out: bytes, rc: int = 0):
        self.stdout = out
        self.returncode = rc

def _patch_fzf(monkeypatch, out: bytes, rc: int = 0):
    from tnotes import picker as P
    # tests must not depend on an fzf binary being installed (CI has none)
    monkeypatch.setattr(P, "has_fzf", lambda: True)
    seen = {}
    def fake_run(argv, input=None, capture_output=False, **kw):
        seen["argv"] = argv
        return _FakeProc(out, rc)
    monkeypatch.setattr(P.subprocess, "run", fake_run)
    return seen

def test_run_picker_ctrl_n_returns_query(monkeypatch):
    from tnotes import picker as P
    seen = _patch_fzf(monkeypatch, b"buy milk\nctrl-n\n")
    rows = [_entry(id="a1b2c3", type="note", title="x", tags=[], scope="global", status="active")]
    assert P.run_picker(rows) == ("ctrl-n", "buy milk")
    exp = next(a for a in seen["argv"] if a.startswith("--expect="))
    assert "ctrl-n" in exp
    assert "--print-query" in seen["argv"]

def test_picker_header_bar_colored_keys(monkeypatch):
    from tnotes import picker as P
    bar = P.header_bar()
    assert "ctrl-n" in bar and "\033[" in bar
    seen = _patch_fzf(monkeypatch, b"\nq\nnope\tx\n")
    P.run_picker([_entry(id="x", type="note", title="t", tags=[], scope="global", status="active")])
    assert "--header" in seen["argv"] and bar in seen["argv"]
    assert "--ansi" in seen["argv"]

def test_run_picker_abort_rc130(monkeypatch):
    from tnotes import picker as P
    _patch_fzf(monkeypatch, b"half-typed\n", rc=130)
    rows = [_entry(id="a1b2c3", type="note", title="x", tags=[], scope="global", status="active")]
    assert P.run_picker(rows) == (None, None)

def test_run_picker_enter_no_match_is_noop(monkeypatch):
    from tnotes import picker as P
    _patch_fzf(monkeypatch, b"nomatch\n\n")
    rows = [_entry(id="a1b2c3", type="note", title="x", tags=[], scope="global", status="active")]
    assert P.run_picker(rows) == (None, None)

def test_run_picker_select_with_query(monkeypatch):
    from tnotes import picker as P
    seen = _patch_fzf(monkeypatch, b"mil\n\n\xf0\x9f\x93\x9d milk \xc2\xb7\ta1b2c3\n")
    rows = [_entry(id="a1b2c3", type="note", title="milk", tags=[], scope="local", status="active")]
    assert P.run_picker(rows) == ("enter", "a1b2c3")

def test_pick_entry_returns_selected(monkeypatch):
    from tnotes import picker as P
    seen = _patch_fzf(monkeypatch, b"\xf0\x9f\x93\x9d milk \xc2\xb7\ta1b2c3\n")
    e = _entry(id="a1b2c3", type="note", title="milk", tags=[], scope="local", status="active")
    assert P.pick_entry([e], prompt="mark done").id == "a1b2c3"
    assert "--prompt" in seen["argv"]
    assert "mark done" in " ".join(seen["argv"])


def test_pick_entry_abort_returns_none(monkeypatch):
    from tnotes import picker as P
    _patch_fzf(monkeypatch, b"", rc=130)
    e = _entry(id="a1b2c3")
    assert P.pick_entry([e]) is None


def test_pick_entry_without_fzf_and_not_tty_is_none(monkeypatch):
    from tnotes import picker as P
    monkeypatch.setattr(P, "has_fzf", lambda: False)
    monkeypatch.setattr(P.sys.stdin, "isatty", lambda: False)
    assert P.pick_entry([_entry(id="a1b2c3")]) is None
