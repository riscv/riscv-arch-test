#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Setup environment for Sargantana after install / cache restore
# Usage: setup-sargantana.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-sargantana.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "SARGANTANA_TILE=$INSTALL_DIR/core_tile" >>"$GITHUB_ENV"

# Reinstall the per-test runner. install-sargantana.sh also installs it, but the simulator
# cache is keyed on install-sargantana.sh alone, so a cache hit would keep an older runner.
install -m 0755 "$(dirname "$0")/run-sargantana.sh" "$INSTALL_DIR/bin/run-sargantana.sh"
