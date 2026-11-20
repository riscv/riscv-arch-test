#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Setup environment for the XiangShan emulator after install / cache restore.
# Usage: setup-xiangshan.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-xiangshan.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "XIANGSHAN_EMU=$INSTALL_DIR/bin/emu" >>"$GITHUB_ENV"
