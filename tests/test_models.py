# tests/test_models.py
import pytest
from tnotes.models import Entry, SCHEMA_VERSION

def test_entry_round_trip():
    e = Entry(id="a1b2c3", type="url", title="t", body="https://x.example",
              tags=["a"], scope="global", cwd=None)
    d = Entry.from_dict(e.to_dict())
    assert d == e and e.to_dict()["schema_version"] == SCHEMA_VERSION == 2

def test_entry_rejects_bad_scope_status_id():
    with pytest.raises(ValueError):
        Entry.from_dict({"id": "a1b2c3", "scope": "everywhere"})
    with pytest.raises(ValueError):
        Entry.from_dict({"id": "a1b2c3", "status": "archived"})
    with pytest.raises(ValueError):
        Entry.from_dict({"id": "XYZ"})

def test_migrate_fills_old_line():
    d = Entry.migrate({"id": "a1b2c3", "title": "t", "body": "b"})
    e = Entry.from_dict(d)
    assert (e.type, e.scope, e.status, e.show_on_open, e.tags) == ("note", "local", "active", True, [])
