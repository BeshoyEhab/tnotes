#!/usr/bin/env bash
# tnotes installer: clone → venv → link tn → shell completions.
#
#   curl -fsSL https://raw.githubusercontent.com/BeshoyEhab/tnotes/master/install.sh | bash
#
# Idempotent: re-running updates an existing ~/tnotes checkout.
# Overrides: TNOTES_INSTALL_DIR (clone location), TNOTES_BIN_DIR (tn symlink).
set -euo pipefail

REPO="https://github.com/BeshoyEhab/tnotes.git"
DIR="${TNOTES_INSTALL_DIR:-$HOME/tnotes}"
BIN_DIR="${TNOTES_BIN_DIR:-$HOME/.local/bin}"

step() { printf '\n==> %s\n' "$*"; }

step "tnotes → $DIR"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only
else
  git clone "$REPO" "$DIR"
fi

cd "$DIR"
if command -v uv >/dev/null 2>&1; then
  step "syncing deps with uv"
  uv sync
else
  step "syncing deps with pip (no uv found)"
  python3 -m venv .venv
  .venv/bin/pip install -q -e .
fi

step "linking tn into $BIN_DIR"
mkdir -p "$BIN_DIR"
ln -sf "$DIR/.venv/bin/tn" "$BIN_DIR/tn"

step "shell completions + fish autoshow"
"$BIN_DIR/tn" completions install

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    printf "\nnote: add %s to your PATH, e.g.\n" "$BIN_DIR"
    printf "  echo 'export PATH=\"%s:\$PATH\"' >> ~/.bashrc\n" "$BIN_DIR"
    ;;
esac

printf '\ndone — try: tn list\n'
