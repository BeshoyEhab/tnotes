from tnotes.models import Entry
from tnotes.tui import selection_actions

def _e(**kw):
    base = dict(id="a1b2c3", type="note", title="t", body="")
    base.update(kw)
    return Entry(**base)

def test_note_links_and_cmds():
    acts = selection_actions(_e(body="see https://a.example, run `make test`"))
    assert acts == {"opens": ["https://a.example"], "runs": ["make test"]}

def test_plain_note_no_actions():
    assert selection_actions(_e(body="just text!")) == {"opens": [], "runs": []}

def test_typed_entries():
    assert selection_actions(_e(type="url", body="https://x.example"))["opens"] == ["https://x.example"]
    assert selection_actions(_e(type="cmd", body="make test"))["runs"] == ["make test"]
