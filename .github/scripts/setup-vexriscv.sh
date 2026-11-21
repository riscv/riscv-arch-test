#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Set up the environment for VexRiscv after install / cache restore
# Usage: setup-vexriscv.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-vexriscv.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "VEXRISCV_SIM=$INSTALL_DIR/bin/vexriscv-tb" >>"$GITHUB_ENV"
