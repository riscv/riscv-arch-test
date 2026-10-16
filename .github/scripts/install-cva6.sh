#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# Build the OpenHW CVA6 Verilator testharness for CI.
# Usage: install-cva6.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.
# Needs riscv64-unknown-elf-gcc on PATH (the setup-tools action provides it in CI).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

INSTALL_DIR="${1:?Usage: install-cva6.sh <install-dir>}"
mkdir -p "$INSTALL_DIR/bin"
INSTALL_DIR="$(cd "$INSTALL_DIR" && pwd)"
CVA6_REPO="https://github.com/openhwfoundation/cva6.git"
CVA6_COMMIT="81245a47fad8fe1a5d562d953ef2662e099def76"
TARGETS="cv32a65x cv32a60x"

export NUM_JOBS="${NUM_JOBS:-$(nproc)}"
export VERILATOR_INSTALL_DIR="$INSTALL_DIR/verilator"
export SPIKE_INSTALL_DIR="$INSTALL_DIR/spike"

# The CVA6 Makefile refuses to run without RISCV; point it at the toolchain on PATH.
gcc_path="$(command -v riscv64-unknown-elf-gcc)" || {
  echo "install-cva6.sh: riscv64-unknown-elf-gcc not on PATH" >&2
  exit 1
}
RISCV="$(dirname "$(dirname "$gcc_path")")"
export RISCV

# 1. Clone CVA6 at the pinned commit. The ISA manual and riscv-dv submodules are not
#    needed to build the testharness.
git init "$INSTALL_DIR/cva6"
(
  cd "$INSTALL_DIR/cva6"
  git remote add origin "$CVA6_REPO"
  git fetch --depth 1 origin "$CVA6_COMMIT"
  git checkout FETCH_HEAD
  mapfile -t submodules < <(git config -f .gitmodules --get-regexp '\.path$' |
    awk '{ print $2 }' | grep -v -e '^docs/' -e '^verif/sim/dv$')
  git submodule update --init --recursive -- "${submodules[@]}"
)

# 2. Verilator and Spike, at the versions CVA6's own CI uses. The testharness links
#    Spike's libfesvr/libriscv/libdisasm, and spike-dasm decodes the debug trace.
bash "$INSTALL_DIR/cva6/verif/regress/install-verilator.sh"
rm -rf "$VERILATOR_INSTALL_DIR"/build-*
bash "$INSTALL_DIR/cva6/verif/regress/install-spike.sh"
export PATH="$VERILATOR_INSTALL_DIR/bin:$PATH"

# 3. Verilate one testharness per target, each in its own work-ver-<target> directory.
#    The directory must be relative to the CVA6 tree: Verilator writes the testbench
#    source paths relative to it.
for target in $TARGETS; do
  make -C "$INSTALL_DIR/cva6" verilate \
    target="$target" \
    verilator="$VERILATOR_INSTALL_DIR/bin/verilator" \
    ver-library="work-ver-$target" \
    TRACE_COMPACT=1
  test -x "$INSTALL_DIR/cva6/work-ver-$target/Variane_testharness"
done

# 4. Install the per-test runners
for target in $TARGETS; do
  install -m 0755 "$SCRIPT_DIR/run-$target.sh" "$INSTALL_DIR/bin/run-$target.sh"
done
