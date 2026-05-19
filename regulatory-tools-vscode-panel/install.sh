#!/usr/bin/env bash
# Install the regulatory panel extension into VS Code via a symlink.
# Run once from this directory; the extension reloads from source on each F5 debug.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VSCODE_EXT_DIR="$HOME/.vscode/extensions"
LINK_NAME="reneeqian.regulatory-panel-dev"

mkdir -p "$VSCODE_EXT_DIR"
ln -snf "$SCRIPT_DIR" "$VSCODE_EXT_DIR/$LINK_NAME"
echo "Linked $SCRIPT_DIR → $VSCODE_EXT_DIR/$LINK_NAME"
echo "Restart VS Code (or Developer: Reload Window) to activate."
