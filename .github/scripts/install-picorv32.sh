#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Install and verilate the PicoRV32 testbench for CI.
# Usage: install-picorv32.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-picorv32.sh <install-dir>}"
PICORV32_REPO="https://github.com/YosysHQ/picorv32.git"
PICORV32_COMMIT="ef203c2b0a3fb793280f5114941416c425c5b461"
VERILATOR_VERSION="v5.036"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$INSTALL_DIR/bin"

# 1. Verilator from source
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(
  cd "$INSTALL_DIR/verilator-src"
  autoconf
  ./configure --prefix="$INSTALL_DIR"
  make -j"$(nproc)"
  make install
)
rm -rf "$INSTALL_DIR/verilator-src"
export PATH="$INSTALL_DIR/bin:$PATH"

# 2. Clone picorv32 at the pinned commit. The repository is archived upstream, so
#    the pin will not move.
git init "$INSTALL_DIR/picorv32"
(
  cd "$INSTALL_DIR/picorv32"
  git remote add origin "$PICORV32_REPO"
  git fetch --depth 1 origin "$PICORV32_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Patch testbench.v. Four edits, none touching picorv32.v itself. They are
#    applied here rather than carried as a fork so that every change to the DUT
#    environment is visible in this script.
cd "$INSTALL_DIR/picorv32"

#    3a. The stock testbench models 128 KB of memory
#        ("reg [31:0] memory [0:128*1024/4-1]", testbench.v:308) against an ACT
#        image of about 285 KB plus a 128 KB stack. An out-of-bounds access
#        prints a message and $finishes, which exits 0 and would silently mask
#        the failure. 8 MB is what a bring-up probe ran at without trouble.
sed -i 's|reg \[31:0\]   memory \[0:128\*1024/4-1\]|reg [31:0]   memory [0:8*1024*1024/4-1]|' testbench.v
#        The two bounds checks must be raised to match. They stay *below* the
#        0x1000_0000 console and 0x2000_0000 pass-register special cases, which
#        are reached only when the address is out of memory range.
sed -i 's|latched_raddr < 128\*1024|latched_raddr < 8*1024*1024|' testbench.v
sed -i 's|latched_waddr < 128\*1024|latched_waddr < 8*1024*1024|' testbench.v

#    3b. Expose the memory model's tests_passed flag as a top-level port so the
#        harness can tell a passing halt from a failing one. It is otherwise an
#        internal wire of picorv32_wrapper.
sed -i 's|^\toutput trap,$|\toutput trap,\n\toutput tests_passed,|' testbench.v
sed -i '/^\twire tests_passed;$/d' testbench.v

#    3b2. On a failing trap the testbench prints "ERROR!" and then calls $stop
#        (testbench.v:272). Verilator's $finish sets a flag and returns rather
#        than unwinding, so the +noerror escape hatch on the line above does not
#        prevent the $stop from executing, and $stop aborts the process from
#        inside eval() before main() can report anything. Turn it into a $finish
#        so the harness stays in control of the exit code.
#        (\x24 is a literal dollar sign; writing it out would be a shell
#        expansion inside double quotes and a shellcheck warning inside single ones)
sed -i 's|^\t\t\t\t[$]stop;$|\t\t\t\t\x24finish;|' testbench.v

#    3c. Configure the core: RV32IMC with fast multiply and divide, misaligned
#        and illegal-instruction catching (both default 1), and the custom IRQ
#        scheme disabled so ecall/ebreak/illegal drive `trap` instead of
#        vectoring to PROGADDR_IRQ. PROGADDR_RESET matches TEST_BASE in link.ld.
sed -i "s|^\t\t\.ENABLE_MUL(1),$|\t\t.ENABLE_FAST_MUL(1),|" testbench.v
sed -i "s|^\t\t\.ENABLE_IRQ(1),$|\t\t.ENABLE_IRQ(0),\n\t\t.PROGADDR_RESET(32'h0000_4000),|" testbench.v

#    Fail loudly if any of the patches did not apply. The upstream repository is
#    archived, so these can only break if the pin above is moved.
expect() { grep -q "$1" testbench.v || {
  echo "install-picorv32.sh: patch check failed, expected $1" >&2
  exit 1
}; }
reject() {
  grep -q "$1" testbench.v && {
    echo "install-picorv32.sh: patch check failed, still found $1" >&2
    exit 1
  }
  return 0
}
expect '0:8\*1024\*1024/4-1'
expect 'output tests_passed,'
expect 'ENABLE_FAST_MUL(1)'
expect "PROGADDR_RESET(32'h0000_4000)"
expect 'ENABLE_IRQ(0)'
reject '[$]stop'
reject '128\*1024'

# 4. Replace picorv32's testbench.cc. The stock one is exit(0) unconditionally
#    with no cycle limit under Verilator, so a hang cannot be told from a pass.
cp "$SCRIPT_DIR/picorv32-act-main.cc" testbench.cc

# 5. Verilate. COMPRESSED_ISA is a preprocessor define, not a parameter.
verilator --cc --exe -Wno-lint -Wno-fatal --top-module picorv32_wrapper \
  -DCOMPRESSED_ISA --Mdir "$INSTALL_DIR/obj_dir" \
  --build -j "$(nproc)" \
  -o Vpicorv32_wrapper \
  testbench.v picorv32.v testbench.cc

# 6. Install the per-test runner
install -m 0755 "$SCRIPT_DIR/run-picorv32.sh" "$INSTALL_DIR/bin/run-picorv32.sh"
