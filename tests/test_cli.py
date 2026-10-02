# tests/test_cli.py
import os
from pathlib import Path
from tnotes.cli import main, compose_in_editor
from tnotes import actions, store

def _add(capsys, *argv):
    assert main(list(argv)) == 0
    return capsys.readouterr().out

def test_quick_add_defaults_local(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    out = _add(capsys, "buy milk")
    eid = out.strip().split()[-1]
    e = store.get_entry(eid)
    assert e.type == "note" and e.scope == "local" and e.cwd == os.path.realpath(os.getcwd())
    assert e.status == "active" and e.show_on_open is True

def test_typed_add_global_no_show_tags(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    out = _add(capsys, "--url", "https://x.example", "--title", "t", "-g", "--tags", "a,b", "--no-show")
    e = store.get_entry(out.strip().split()[-1])
    assert (e.type, e.scope, e.tags, e.show_on_open) == ("url", "global", ["a", "b"], False)

def test_done_undone_hide_unhide_rm(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    eid = _add(capsys, "tmp").strip().split()[-1]
    assert main(["done", eid]) == 0 and store.get_entry(eid).status == "done"
    assert main(["undone", eid]) == 0 and store.get_entry(eid).status == "active"
    assert main(["hide", eid]) == 0 and store.get_entry(eid).show_on_open is False
    assert main(["unhide", eid]) == 0 and store.get_entry(eid).show_on_open is True
    assert main(["rm", eid]) == 0 and store.get_entry(eid) is None

def test_editor_failure_keeps_draft(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.setattr(actions, "edit_in_editor", lambda p: 1)
    assert compose_in_editor("note", "hi") is None
    tmp = capsys.readouterr().out.strip().split()[-1]
    assert Path(tmp).exists()
    e = store.add_entry(type="note", title="t", body="b", tags=[], scope="global", cwd=None, show_on_open=True)
    assert main(["edit", e.id]) == 1
    tmp = capsys.readouterr().out.strip().split()[-1]
    assert Path(tmp).exists()

def test_show_startup_silent_when_empty(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    assert main(["show", "--startup"]) == 0
    assert capsys.readouterr().out == ""

def test_show_startup_compact_like_old_note(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="g", body="g-body", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    store.add_entry(type="note", title="l", body="l-body", tags=[],
                    scope="local", cwd=os.path.realpath(os.getcwd()),
                    show_on_open=True)
    assert main(["show", "--startup", "--all"]) == 0
    out = capsys.readouterr().out
    assert "Body (wrapped)" not in out and "Actions:" not in out
    assert "Global" in out and "This folder" in out
    assert "  1. " in out and "g-body" not in out and "l-body" not in out

def test_show_startup_shows_ids(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="g", body="g-body", tags=[],
                        scope="global", cwd=None, show_on_open=True)
    assert main(["show", "--startup", "--all"]) == 0
    assert e.id in capsys.readouterr().out

def test_done_numeric_out_of_range_hints_list(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    store.add_entry(type="note", title="only", body="b", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    assert main(["done", "9999999"]) == 1
    assert "tn list" in capsys.readouterr().err

def test_preview_caps_100_lines(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    body = "\n".join(f"line {i}" for i in range(150))
    e = store.add_entry(type="note", title="big", body=body, tags=[],
                        scope="global", cwd=None, show_on_open=True)
    assert main(["show", e.id, "--preview"]) == 0
    out = capsys.readouterr().out
    assert "… (+50 lines, Enter for full)" in out
    assert "line 99" in out and "line 100" not in out

def test_list_hides_done_unless_flag(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="t", body="b", tags=[], scope="global", cwd=None, show_on_open=True)
    store.update_entry(e.id, status="done")
    assert main(["list"]) == 0
    assert e.id not in capsys.readouterr().out
    assert main(["list", "--done"]) == 0
    assert e.id in capsys.readouterr().out

def test_ambiguous_prefix_rm_deletes_nothing(tmp_path, monkeypatch, capsys):
    import json
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    def _ent(eid):
        return {"id": eid, "type": "note", "title": "t", "body": "b", "tags": [],
                "scope": "global", "cwd": None, "status": "active",
                "show_on_open": True, "created": "t", "updated": "t"}
    (tmp_path / "tnotes.jsonl").write_text(
        json.dumps(_ent("abcdef")) + "\n" + json.dumps(_ent("abc123")) + "\n",
        encoding="utf-8")
    assert main(["rm", "abc"]) == 1
    ids = {e.id for e in store.load_all()}
    assert ids == {"abcdef", "abc123"}

def test_open_invalid_index_no_traceback(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    e = store.add_entry(type="note", title="t", body="b", tags=[],
                        scope="global", cwd=None, show_on_open=True)
    assert main(["open", e.id, "foo"]) == 1
    err = capsys.readouterr().err
    assert "invalid index" in err

def test_ctrl_n_compose_saves_note(tmp_path, monkeypatch, capsys):
    import os
    from tnotes import cli as C
    from tnotes.cli_actions import dispatch
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    import tnotes.picker as P
    monkeypatch.setattr(P, "run_picker", lambda entries: ("ctrl-n", "buy milk"))
    monkeypatch.setattr(C, "compose_in_editor", lambda et, initial="": "buy milk\n")
    args = C.build_parser().parse_args([])
    assert dispatch(args) == 0
    assert "saved" in capsys.readouterr().out
    assert len(store.load_all()) == 1

def test_empty_store_goes_to_compose(tmp_path, monkeypatch, capsys):
    from tnotes import cli as C
    from tnotes.cli_actions import dispatch
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(C, "compose_in_editor", lambda et, initial="": "first!\n")
    assert dispatch(C.build_parser().parse_args([])) == 0
    assert "saved" in capsys.readouterr().out

def test_preview_mdcat_when_present(tmp_path, monkeypatch, capsys):
    import shutil
    import tnotes.cli_read as R
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.setenv("FZF_PREVIEW_COLUMNS", "60")
    monkeypatch.setattr(shutil, "which", lambda n: "/usr/bin/mdcat" if n == "mdcat" else None)
    def fake_run(cmd, input=None, capture_output=False, **kw):
        assert "mdcat" in cmd[0] and "--ansi" in cmd
        class P2:
            returncode = 0
            stdout = b"PRETTY:" + (input or b"")
        return P2()
    monkeypatch.setattr(R.subprocess, "run", fake_run)
    e = store.add_entry(type="note", title="t", body="hello", tags=[], scope="global", cwd=None, show_on_open=True)
    assert main(["show", e.id, "--preview"]) == 0
    assert "PRETTY:" in capsys.readouterr().out

def test_preview_plain_without_mdcat(tmp_path, monkeypatch, capsys):
    import shutil
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.setattr(shutil, "which", lambda n: None)
    e = store.add_entry(type="note", title="t", body="hello", tags=[], scope="global", cwd=None, show_on_open=True)
    assert main(["show", e.id, "--preview"]) == 0
    out = capsys.readouterr().out
    assert "hello" in out and "PRETTY:" not in out

def test_tui_subcommand_routes_to_picker(tmp_path, monkeypatch, capsys):
    import sys
    import tnotes.cli_actions as A
    import tnotes.picker as P
    import tnotes.tui as T
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    store.add_entry(type="note", title="x", body="b", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    # no terminal here: explicit tui must error clearly, not silently fzf
    monkeypatch.setattr(P, "run_picker", lambda entries: (_ for _ in ()).throw(
        AssertionError("fzf fallback must not run for tn tui")))
    assert main(["tui"]) == 1
    assert "interactive terminal" in capsys.readouterr().err
    # ...but with a terminal it always launches the TUI, even when empty
    for e in store.load_all():
        assert store.delete_entry(e.id)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    launched = {}
    class FakeApp:
        def __init__(self, **kwargs):
            launched.update(kwargs)
        def run(self):
            launched["ran"] = True
    monkeypatch.setattr(T, "TnotesApp", FakeApp)
    monkeypatch.setattr(A, "_compose_new_note", lambda *a: (_ for _ in ()).throw(
        AssertionError("editor must not open for tn tui")))
    assert main(["tui"]) == 0
    assert launched.get("ran") is True
    assert len(store.load_all()) == 0  # editor never ran, nothing added
    assert main(["tui", "--all"]) == 0
    assert launched.get("all_dirs") is True

def test_list_color_when_enabled_no_color_when_env(tmp_path, monkeypatch, capsys):
    import tnotes.cli_read as R
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="t", body="b", tags=["a"], scope="global",
                    cwd=None, show_on_open=True)
    monkeypatch.setattr(R, "_color_enabled", lambda: True)
    assert main(["list"]) == 0
    assert "\033[" in capsys.readouterr().out
    monkeypatch.setattr(R, "_color_enabled", lambda: False)
    assert main(["list"]) == 0
    assert "\033[" not in capsys.readouterr().out

def test_color_gate_respects_env(tmp_path, monkeypatch, capsys):
    import tnotes.cli_read as R
    assert R._color_enabled() is False  # pytest stdout is not a tty
    monkeypatch.setenv("NO_COLOR", "1")
    assert R._color_enabled() is False
    monkeypatch.delenv("NO_COLOR")
    monkeypatch.setenv("TERM", "dumb")
    assert R._color_enabled() is False

def test_startup_headers_bold_when_color(tmp_path, monkeypatch, capsys):
    import tnotes.cli_read as R
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    store.add_entry(type="note", title="g", body="b", tags=[],
                    scope="global", cwd=None, show_on_open=True)
    monkeypatch.setattr(R, "_color_enabled", lambda: True)
    assert main(["show", "--startup", "--all"]) == 0
    out = capsys.readouterr().out
    assert "\033[1mGlobal notes:\033[0m" in out
