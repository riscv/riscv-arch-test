#!/usr/bin/env bash
# Marin Radic mradic07@gmail.com
# SPDX-License-Identifier: Apache-2.0
# Setup environment for cve2 after install / cache restore
# Usage: setup-cve2.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-cve2.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "CVE20_DV_ROOT=$INSTALL_DIR/cv32e20-dv" >>"$GITHUB_ENV"
