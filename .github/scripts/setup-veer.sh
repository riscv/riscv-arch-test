#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Setup environment for VeeR after install / cache restore
# Usage: setup-veer.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-veer.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >> "$GITHUB_PATH"
echo "VEER_SNAPSHOT=$INSTALL_DIR/eh1" >> "$GITHUB_ENV"
