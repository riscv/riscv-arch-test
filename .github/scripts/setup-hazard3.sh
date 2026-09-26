#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Set up the environment for Hazard3 after install / cache restore
# Usage: setup-hazard3.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-hazard3.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "HAZARD3_SIM=$INSTALL_DIR/bin/hazard3-tb" >>"$GITHUB_ENV"
