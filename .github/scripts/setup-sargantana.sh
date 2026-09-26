#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Setup environment for Sargantana after install / cache restore
# Usage: setup-sargantana.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-sargantana.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "SARGANTANA_TILE=$INSTALL_DIR/core_tile" >>"$GITHUB_ENV"
