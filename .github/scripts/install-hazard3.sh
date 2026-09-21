#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
# Build the Hazard3 reference testbench (Verilator) for CI.
# Usage: install-hazard3.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-hazard3.sh <install-dir>}"
HAZARD3_REPO="https://github.com/Wren6991/Hazard3.git"
HAZARD3_COMMIT="8af992930f71a69b0e06c38734c1094f41a05ca0" # v1.1.1
VERILATOR_VERSION="v5.036"

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

# 2. Clone Hazard3 at the pinned commit
git init "$INSTALL_DIR/Hazard3"
(
  cd "$INSTALL_DIR/Hazard3"
  git remote add origin "$HAZARD3_REPO"
  git fetch --depth 1 origin "$HAZARD3_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Write the RTL configuration this ACT config is written against.
#
#    This is the bundled config_pmpfull.vh (the RP2350 feature set plus Zbc and 16 PMP
#    regions), with five deliberate changes:
#      * RESET_VECTOR moved to 0x80000000, the base of the testbench's RAM, because the
#        image is loaded as a flat binary at MEM_BASE and there is no boot ROM.
#      * EXTENSION_XH3IRQ = 0. With the nonstandard interrupt controller enabled, external
#        interrupts arrive through a 512-source priority controller and its meiea/meipa
#        CSRs instead of plain mip.MEIP, and ACT's external-interrupt tests never see the
#        interrupt.
#      * EXTENSION_XH3BEXTM / XH3PMPM / XH3POWER = 0: custom extensions with no ACT suite,
#        which occupy encodings ACT expects to be illegal.
#      * EXTENSION_ZILSD / ZCLSD / ZCMP = 0: frozen rather than ratified, no ACT suite, and
#        the RISC-V GCC 15.2 multilib set has no Zcmp library.
#      * MVENDORID_VAL / MCONFIGPTR_VAL set to 0. The bundled values (0xdeadbeef,
#        0x9abcdef0) are placeholders; the manual permits all-zeroes for both, and that is
#        what VENDOR_ID_BANK/VENDOR_ID_OFFSET and CONFIG_PTR_ADDRESS in the UDB config say.
cat >"$INSTALL_DIR/Hazard3/test/sim/tb_common/hdl/config_act.vh" <<'EOF'
// Hazard3 configuration for riscv-arch-test: maximum ratified feature set.

localparam RESET_VECTOR        = 32'h80000000;
localparam MTVEC_INIT          = 32'h80000000;
localparam EXTENSION_A         = 1;
localparam EXTENSION_C         = 1;
localparam EXTENSION_E         = 0;
localparam EXTENSION_M         = 1;
localparam EXTENSION_ZBA       = 1;
localparam EXTENSION_ZBB       = 1;
localparam EXTENSION_ZBC       = 1;
localparam EXTENSION_ZBKB      = 1;
localparam EXTENSION_ZBKX      = 1;
localparam EXTENSION_ZBS       = 1;
localparam EXTENSION_ZCB       = 1;
localparam EXTENSION_ZCLSD     = 0;
localparam EXTENSION_ZCMP      = 0;
localparam EXTENSION_ZIFENCEI  = 1;
localparam EXTENSION_ZILSD     = 0;
localparam EXTENSION_XH3BEXTM  = 0;
localparam EXTENSION_XH3IRQ    = 0;
localparam EXTENSION_XH3PMPM   = 0;
localparam EXTENSION_XH3POWER  = 0;
localparam CSR_M_MANDATORY     = 1;
localparam CSR_M_TRAP          = 1;
localparam CSR_COUNTER         = 1;
localparam U_MODE              = 1;
localparam PMP_REGIONS         = 16;
localparam PMP_GRAIN           = 0;
localparam PMP_MATCH_NAPOT     = 1;
localparam PMP_MATCH_TOR       = 1;
localparam PMP_HARDWIRED       = {(PMP_REGIONS > 0 ? PMP_REGIONS : 1){1'b0}};
localparam PMP_HARDWIRED_ADDR  = {(PMP_REGIONS > 0 ? PMP_REGIONS : 1){32'h0}};
localparam PMP_HARDWIRED_CFG   = {(PMP_REGIONS > 0 ? PMP_REGIONS : 1){8'h00}};
localparam DEBUG_SUPPORT       = 1;
localparam BREAKPOINT_TRIGGERS = 4;
localparam NUM_IRQS            = 32;
localparam IRQ_PRIORITY_BITS   = 4;
localparam IRQ_INPUT_BYPASS    = {NUM_IRQS{1'b0}};
localparam MVENDORID_VAL       = 32'h00000000;
localparam MCONFIGPTR_VAL      = 32'h00000000;
localparam REDUCED_BYPASS      = 0;
localparam MULDIV_UNROLL       = 2;
localparam MUL_FAST            = 1;
localparam MUL_FASTER          = 1;
localparam MULH_FAST           = 1;
localparam FAST_BRANCHCMP      = 1;
localparam RESET_REGFILE       = 1;
localparam BRANCH_PREDICTOR    = 1;
localparam MTVEC_WMASK         = 32'hfffffffd;
EOF

# 4. Verilate and build.
#
#    Two notes on the bundled Makefile:
#      * BUILD_DIR is keyed on the flist, not on CONFIG, and the verilate stamp does not
#        depend on config_*.vh, so a build directory left over from a different CONFIG is
#        silently relinked. Always start from a clean tree, as this script does.
#      * The vlib rule forces a precompiled header (a workaround for a Verilator issue with
#        clang) that makes GCC spend over ten minutes in a single cc1plus. Driving the
#        generated Vtb.mk directly avoids it, so the two stamp files are made by hand.
(
  cd "$INSTALL_DIR/Hazard3/test/sim/tb_verilator"
  make CONFIG=act vcc
  make -j"$(nproc)" -C build-tb/obj_dir -f Vtb.mk
  touch build-tb/vlib.touch
  make CONFIG=act
)

install -m 0755 "$INSTALL_DIR/Hazard3/test/sim/tb_verilator/tb-act" "$INSTALL_DIR/bin/hazard3-tb"

# 5. Install the per-test runner
install -m 0755 "$(dirname "$0")/run-hazard3.sh" "$INSTALL_DIR/bin/run-hazard3.sh"
