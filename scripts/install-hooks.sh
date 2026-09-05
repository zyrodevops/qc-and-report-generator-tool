#!/usr/bin/env bash
# Install project git hooks
set -e
ROOT_DIR="$(git rev-parse --show-toplevel)"
mkdir -p "$ROOT_DIR/.git/hooks"
cp "$ROOT_DIR/scripts/hooks/pre-commit" "$ROOT_DIR/.git/hooks/pre-commit"
chmod +x "$ROOT_DIR/.git/hooks/pre-commit"
chmod +x "$ROOT_DIR/scripts/hooks/pre-commit"
git config core.hooksPath scripts/hooks
echo "Pre-commit hook installed successfully into .git/hooks/pre-commit and git core.hooksPath configured."
