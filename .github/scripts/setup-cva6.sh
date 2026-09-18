#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Setup environment for CVA6 after install-cva6.sh / cache restore.
# Usage: setup-cva6.sh <install-dir>
#
# Local use (print exports for eval):
#   eval "$(bash .github/scripts/setup-cva6.sh ./cva6 --print)"

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-cva6.sh <install-dir>}"
PRINT="${2:-}"

CVA6_ROOT="$(readlink -f "${INSTALL_DIR}/cva6")"

if [[ "$PRINT" == "--print" ]]; then
  printf 'export PATH=%q:$PATH\n' "${INSTALL_DIR}/bin"
  printf 'export CVA6_ROOT=%q\n' "${CVA6_ROOT}"
  exit 0
fi

if [[ -n "${GITHUB_PATH:-}" ]]; then
  echo "${INSTALL_DIR}/bin" >>"$GITHUB_PATH"
fi
if [[ -n "${GITHUB_ENV:-}" ]]; then
  echo "CVA6_ROOT=${CVA6_ROOT}" >>"$GITHUB_ENV"
fi
