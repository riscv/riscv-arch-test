#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Set up the environment for CVA6 after install / cache restore
# Usage: setup-cva6.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-cva6.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "CVA6_SNAPSHOT=$INSTALL_DIR" >>"$GITHUB_ENV"
