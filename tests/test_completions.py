# tests/test_completions.py
import shutil
import subprocess
from pathlib import Path

import pytest

from tnotes import completions as C
from tnotes.cli import main


def _fake_home(tmp_path, monkeypatch, shells=("fish", "bash")):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setattr(C.shutil, "which",
                        lambda n: f"/usr/bin/{n}" if n in shells else None)
    return home


def _files(home):
    return {
        "fish_comp": home / ".config/fish/completions/tn.fish",
        "fish_hook": home / ".config/fish/conf.d/tnotes-autoshow.fish",
        "bash": home / ".local/share/bash-completion/completions/tn",
        "zsh": home / ".zsh/completions/_tn",
    }


def test_completions_install_writes_only_detected_shells(tmp_path, monkeypatch, capsys):
    home = _fake_home(tmp_path, monkeypatch, shells=("fish", "bash"))
    assert main(["completions", "install"]) == 0
    out = capsys.readouterr().out
    f = _files(home)
    assert f["fish_comp"].exists() and f["fish_hook"].exists() and f["bash"].exists()
    assert not f["zsh"].exists()  # zsh not detected
    assert "fish completion" in out and "fish autoshow hook" in out
    assert "bash completion" in out and "zsh" not in out
    assert f["fish_comp"].read_text(encoding="utf-8").startswith("# fish")


def test_completions_install_idempotent_then_uninstall(tmp_path, monkeypatch, capsys):
    home = _fake_home(tmp_path, monkeypatch, shells=("fish",))
    assert main(["completions"]) == 0  # bare = install
    assert main(["completions", "install"]) == 0
    f = _files(home)
    assert f["fish_comp"].exists()
    assert main(["completions", "uninstall"]) == 0
    assert not f["fish_comp"].exists() and not f["fish_hook"].exists()
    capsys.readouterr()
    assert main(["completions", "uninstall"]) == 0  # second time: reported, not fatal
    assert "absent (skipped)" in capsys.readouterr().out


def test_completions_zsh_hint_printed(tmp_path, monkeypatch, capsys):
    home = _fake_home(tmp_path, monkeypatch, shells=("zsh",))
    assert main(["completions", "install"]) == 0
    out = capsys.readouterr().out
    assert _files(home)["zsh"].exists()
    assert "fpath=" in out and str(home / ".zsh" / "completions") in out


def test_completions_no_shell_detected_is_clean(tmp_path, monkeypatch, capsys):
    _fake_home(tmp_path, monkeypatch, shells=())
    assert main(["completions", "install"]) == 0
    assert "nothing installed" in capsys.readouterr().out


def test_shipped_scripts_tolerate_numbered_rows():
    # `tn list` rows are "1. ✔ 📝 title · id": before any '^✔' match or field
    # parse, the scripts must strip the leading number.
    data = Path(C._DATA)
    for name in ("_tn", "tn.fish", "tn.bash"):
        text = (data / name).read_text(encoding="utf-8")
        assert "s/^[0-9]+\\. //" in text, name
        for line in text.splitlines():
            if "grep '^✔'" in line:
                assert "s/^[0-9]+\\. //" in line, name  # strip before the anchor


def test_bash_completion_offers_row_numbers(tmp_path):
    # The row is what `tn done N` addresses, so completion values must be
    # numbers — ids like 1a2b3c made `tn done 1<TAB>` insert the wrong entry.
    fixture = tmp_path / "rows.txt"
    fixture.write_text(
        "1. 📝 alpha · aa000a\n"
        "2. ✔ 📝 beta · bb000b\n"
        "3. 📝 gamma · cc000c\n", encoding="utf-8")
    script = f'''
tn() {{ cat {fixture}; }}
source {Path(C._DATA) / "tn.bash"}
_tn_active_numbers
echo ---
_tn_done_numbers
'''
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True)
    active, done = out.stdout.split("---\n")
    assert active.split() == ["1", "2", "3"]
    assert done.split() == ["2"]


def test_fish_completion_offers_row_number_not_id_prefix(tmp_path):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("fish not installed")
    fixture = tmp_path / "rows.txt"
    # row 1's id deliberately does not start with 1; row 2's does.
    fixture.write_text(
        "1. 📝 first · 2b000b\n"
        "2. 📝 hash · 1a2b3c\n", encoding="utf-8")
    script = f'''
set -g fish_complete_path /nonexistent
function tn; cat {fixture}; end
source {Path(C._DATA) / "tn.fish"}
complete -C "tn done 1"
'''
    out = subprocess.run([fish, "-c", script], capture_output=True, text=True, check=True)
    values = [line.split("\t")[0] for line in out.stdout.splitlines() if line.strip()]
    assert values == ["1"]


def test_fish_done_completion_strips_check_and_type_glyph(tmp_path):
    fish = shutil.which("fish")
    if fish is None:
        pytest.skip("fish not installed")
    fixture = tmp_path / "rows.txt"
    fixture.write_text(
        "1. ✎ active · aa000a\n"
        "2. ✔ ✎ finished · bb000b\n", encoding="utf-8")
    script = f'''
set -g fish_complete_path /nonexistent
function tn; cat {fixture}; end
source {Path(C._DATA) / "tn.fish"}
complete -C "tn undone "
'''
    out = subprocess.run([fish, "-c", script], capture_output=True, text=True, check=True)
    lines = [line for line in out.stdout.splitlines() if line.strip()]
    assert lines == ["2\tfinished"]


def test_zsh_completion_offers_row_numbers():
    text = (Path(C._DATA) / "_tn").read_text(encoding="utf-8")
    assert 'printf "%s:%s\\n", NR, $0' in text
    # the done branch drops both the check mark and the type glyph
    assert 'sub(/^✔ /,""); sub(/^[^ ]+ /,"")' in text


def test_install_replaces_dangling_symlink(tmp_path, monkeypatch):
    # upgrading from the old `ln -sf ~/tnotes/fish/...` setup leaves symlinks
    # pointing at moved files: install must replace them, not crash
    home = _fake_home(tmp_path, monkeypatch, shells=("fish",))
    f = _files(home)
    f["fish_comp"].parent.mkdir(parents=True)
    f["fish_comp"].symlink_to(tmp_path / "gone" / "tn.fish")  # dangling
    f["fish_hook"].parent.mkdir(parents=True)
    f["fish_hook"].symlink_to(tmp_path / "gone" / "tnotes-autoshow.fish")
    assert main(["completions", "install"]) == 0
    assert f["fish_comp"].is_file() and not f["fish_comp"].is_symlink()
    assert f["fish_hook"].is_file() and not f["fish_hook"].is_symlink()
    assert "complete -c tn" in f["fish_comp"].read_text(encoding="utf-8")
