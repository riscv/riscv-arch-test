#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Setup environment for cve4 after install / cache restore                                                                                                  
# Usage: setup-cve4.sh <install-dir>

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-cve4.sh <install-dir>}"

echo "$INSTALL_DIR/bin" >> "$GITHUB_PATH"
echo "CVE$_DV_ROOT=$INSTALL_DIR/cv32e40p-dv" >> "$GITHUB_ENV"

