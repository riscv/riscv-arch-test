#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Set up the environment for Rocket + Saturn + H after install / cache restore
# Usage: setup-rocket.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-rocket.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "ROCKET_SIM=$INSTALL_DIR/bin/simulator-rocket-saturn-h" >>"$GITHUB_ENV"
