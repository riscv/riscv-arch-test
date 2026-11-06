#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Set up the environment for BOOM after install / cache restore
# Usage: setup-boom.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-boom.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "BOOM_SIM=$INSTALL_DIR/bin/simulator-boom" >>"$GITHUB_ENV"
