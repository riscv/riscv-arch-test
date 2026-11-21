#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Set up the environment for NEORV32 after install / cache restore
# Usage: setup-neorv32.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-neorv32.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "NEORV32_SIM=$INSTALL_DIR/bin/neorv32-tb" >>"$GITHUB_ENV"
