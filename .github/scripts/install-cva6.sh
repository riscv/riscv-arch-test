#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Install CVA6 Verilator testharness for ACT (cv32a65x).
# Usage: install-cva6.sh <install-dir>
#   Typical: install-cva6.sh ./cva6
# Creates: <install-dir>/bin/run-cv32a65x.sh and <install-dir>/cva6/ (source tree).
# Cache key derives from sha256(this file)[:12]; bump CVA6_COMMIT to invalidate.
#
# Override fork/commit:
#   CVA6_REPO=https://github.com/you/cva6.git CVA6_COMMIT=<sha> install-cva6.sh ./cva6
# Or populate <install-dir>/cva6/ manually (clone/copy) before running install.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-cva6.sh <install-dir>}"
CVA6_REPO="${CVA6_REPO:-https://github.com/openhwgroup/cva6.git}"
# Pin: bump when updating the CVA6-side runner or RTL integration.
CVA6_COMMIT="${CVA6_COMMIT:-01ffe61f}"
CVA6_TREE="${INSTALL_DIR}/cva6"

mkdir -p "${INSTALL_DIR}/bin"

# 1. CVA6 sources under <install-dir>/cva6/ (same layout as cve2/cv32e20-dv).
if [[ ! -f "${CVA6_TREE}/Makefile" ]]; then
  mkdir -p "${CVA6_TREE}"
  git init "${CVA6_TREE}"
  (
    cd "${CVA6_TREE}"
    git remote add origin "${CVA6_REPO}"
    git fetch --depth 1 origin "${CVA6_COMMIT}"
    git checkout FETCH_HEAD
    git submodule update --init --recursive
  )
fi

CVA6_ROOT="$(readlink -f "${CVA6_TREE}")"
export RISCV="${CVA6_ROOT}/tools/riscv"
export VERILATOR_INSTALL_DIR="${CVA6_ROOT}/tools/verilator"

# 2. RISC-V toolchain and Verilator under ${CVA6_ROOT}/tools/.
bash "${CVA6_ROOT}/verif/regress/install-toolchain.sh"
bash "${CVA6_ROOT}/verif/regress/install-verilator.sh"
export PATH="${VERILATOR_INSTALL_DIR}/bin:${RISCV}/bin:${PATH}"

# 3. Build Verilator testharness for cv32a65x.
make -C "${CVA6_ROOT}" verilate \
  verilator="verilator --no-timing" \
  target=cv32a65x \
  TRACE_COMPACT=1 \
  NUM_JOBS="${NUM_JOBS:-$(nproc)}"

test -x "${CVA6_ROOT}/work-ver/Variane_testharness" || {
  echo "ERROR: Variane_testharness not built under ${CVA6_ROOT}/work-ver/" >&2
  exit 1
}

# 4. Install ACT ELF runner into <install-dir>/bin/ (requires CVA6_ROOT when invoked).
install -m 0755 "${CVA6_ROOT}/.github/scripts/run-cv32a65x.sh" \
  "${INSTALL_DIR}/bin/run-cv32a65x.sh"
