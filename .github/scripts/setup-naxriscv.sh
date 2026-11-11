#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Set up the environment for NaxRiscv after install / cache restore
# Usage: setup-naxriscv.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-naxriscv.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "NAXRISCV_SIM=$INSTALL_DIR/bin/VNaxRiscv" >>"$GITHUB_ENV"
