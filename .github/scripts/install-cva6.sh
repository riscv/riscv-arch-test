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

# Replace the testharness GPIO error slave with an interrupt generator compatible with
# Sail's simple_interrupt_generator, so tests can raise machine external interrupts.
patch -p1 -l -d "$INSTALL_DIR/cva6" <<'ACT_CVA6_TB_PATCH'
--- a/corev_apu/tb/ariane_testharness.sv
+++ b/corev_apu/tb/ariane_testharness.sv
@@ -375,24 +375,45 @@
   // GPIO
   // ------------------------------

-  // GPIO not implemented, adding an error slave here
+  // ACT patch: interrupt generator in the GPIO slot, compatible with Sail's
+  // simple_interrupt_generator. Offset 0 reads the version (0x00010001). A write to
+  // offset 4 with bit 11 (MEI) set raises (bit 31 = 1) or clears (bit 31 = 0) the
+  // machine external interrupt input of the core.
+  logic                         act_irq_req;
+  logic                         act_irq_we;
+  logic [AXI_ADDRESS_WIDTH-1:0] act_irq_addr;
+  logic [AXI_DATA_WIDTH/8-1:0]  act_irq_be;
+  logic [AXI_DATA_WIDTH-1:0]    act_irq_wdata;
+  logic                         act_mei;

-  ariane_axi_soc::req_slv_t  gpio_req;
-  ariane_axi_soc::resp_slv_t gpio_resp;
-  `AXI_ASSIGN_TO_REQ(gpio_req, master[ariane_soc::GPIO])
-  `AXI_ASSIGN_FROM_RESP(master[ariane_soc::GPIO], gpio_resp)
-  axi_err_slv #(
-    .AxiIdWidth ( ariane_axi_soc::IdWidthSlave ),
-    .req_t      ( ariane_axi_soc::req_slv_t    ),
-    .resp_t     ( ariane_axi_soc::resp_slv_t   )
-  ) i_gpio_err_slv (
-    .clk_i      ( clk_i      ),
-    .rst_ni     ( ndmreset_n ),
-    .test_i     ( test_en    ),
-    .slv_req_i  ( gpio_req ),
-    .slv_resp_o ( gpio_resp )
+  axi2mem #(
+    .AXI_ID_WIDTH   ( ariane_axi_soc::IdWidthSlave ),
+    .AXI_ADDR_WIDTH ( AXI_ADDRESS_WIDTH            ),
+    .AXI_DATA_WIDTH ( AXI_DATA_WIDTH               ),
+    .AXI_USER_WIDTH ( AXI_USER_WIDTH               )
+  ) i_act_irq_axi2mem (
+    .clk_i  ( clk_i                    ),
+    .rst_ni ( ndmreset_n               ),
+    .slave  ( master[ariane_soc::GPIO] ),
+    .req_o  ( act_irq_req              ),
+    .we_o   ( act_irq_we               ),
+    .addr_o ( act_irq_addr             ),
+    .be_o   ( act_irq_be               ),
+    .user_o (                          ),
+    .data_o ( act_irq_wdata            ),
+    .user_i ( '0                       ),
+    .data_i ( 64'h0000_0000_0001_0001  )
   );

+  always_ff @(posedge clk_i or negedge ndmreset_n) begin
+    if (!ndmreset_n) begin
+      act_mei <= 1'b0;
+    end else if (act_irq_req && act_irq_we && act_irq_addr[11:0] == 12'h004
+                 && act_irq_be[4] && act_irq_wdata[32+11]) begin
+      act_mei <= act_irq_wdata[32+31];
+    end
+  end
+

   // ------------------------------
   // Memory + Exclusive Access
@@ -643,7 +664,7 @@
     .rst_ni               ( ndmreset_n          ),
     .boot_addr_i          ( ariane_soc::ROMBase ), // start fetching from ROM
     .hart_id_i            ( {56'h0, hart_id}    ),
-    .irq_i                ( irqs                ),
+    .irq_i                ( irqs | {1'b0, act_mei} ),
     .ipi_i                ( ipi                 ),
     .time_irq_i           ( timer_irq           ),
     .rvfi_probes_o        ( rvfi_probes         ),
ACT_CVA6_TB_PATCH

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

# 4. Install the shared per-test runner (the core is chosen with --target)
install -m 0755 "$SCRIPT_DIR/run-cva6.sh" "$INSTALL_DIR/bin/run-cva6.sh"
