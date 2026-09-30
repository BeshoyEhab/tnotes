# tests/test_config.py
from tnotes import config

def test_config_defaults(monkeypatch):
    for k in ("TNOTES_DIR", "EDITOR", "VISUAL", "BROWSER", "PAGER", "NOTE_AUTOSHOW_GLOBAL"):
        monkeypatch.delenv(k, raising=False)
    assert config.data_dir().name == "tnotes"
    assert config.editor() == "vi" and config.browser() is None
    assert config.pager() == "less -R" and config.autoshow_global() is False

def test_config_overrides(monkeypatch, tmp_path):
    monkeypatch.setenv("TNOTES_DIR", str(tmp_path))
    monkeypatch.setenv("EDITOR", "hx")
    monkeypatch.setenv("NOTE_AUTOSHOW_GLOBAL", "1")
    assert config.data_dir() == tmp_path and config.editor() == "hx"
    assert config.autoshow_global() is True
