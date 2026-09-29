from tnotes.extract import extract_actions

def test_url_entry_yields_open():
    acts = extract_actions({"type": "url", "title": "py", "body": "https://docs.python.org/x"})
    assert acts[0] == {"kind": "open", "target": "https://docs.python.org/x", "label": "py"}

def test_cmd_entry_yields_run():
    acts = extract_actions({"type": "cmd", "title": "t", "body": "docker ps -a"})
    assert acts == [{"kind": "run", "target": "docker ps -a", "label": "t"}]

def test_inline_link_bare_backtick_fenced():
    body = ("see [guide](https://example.com/a) and https://bare.example/b. "
            "run `docker ps -a` then:\n```sh\necho hi\nmake test\n```")
    acts = extract_actions({"type": "note", "title": "n", "body": body})
    targets = [(a["kind"], a["target"]) for a in acts]
    assert ("open", "https://example.com/a") in targets
    assert ("open", "https://bare.example/b") in targets  # trailing . stripped
    assert ("run", "docker ps -a") in targets
    assert ("run", "echo hi") in targets
    assert ("run", "make test") in targets

def test_bang_backslash_untouched():
    acts = extract_actions({"type": "note", "title": "n", "body": r"wow! C:\path\file ~user"})
    assert acts == []
