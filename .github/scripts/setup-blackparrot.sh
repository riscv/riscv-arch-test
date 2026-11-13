#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Setup environment for BlackParrot after install / cache restore
# Usage: setup-blackparrot.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-blackparrot.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "BLACKPARROT_SIM=$INSTALL_DIR/black-parrot/bp_top/verilator/results/bp_tethered.e_bp_unicore_cfg/simsc" >>"$GITHUB_ENV"
