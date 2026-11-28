#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build a verilated XuanTie OpenE906 smart_run SoC testbench for CI.
# Usage: install-e906.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-e906.sh <install-dir>}"
E906_REPO="https://github.com/T-head-Semi/opene906.git"
E906_COMMIT="c5b878958e73e0b8f324a8132943f184a7831c07"
VERILATOR_VERSION="v5.052"
JOBS="${JOBS:-$(nproc)}"

mkdir -p "$INSTALL_DIR/bin"

# 1. Verilator from source
git clone --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
(
  cd "$INSTALL_DIR/verilator-src"
  autoconf
  ./configure --prefix="$INSTALL_DIR"
  make -j"$JOBS"
  make install
)
rm -rf "$INSTALL_DIR/verilator-src"
export PATH="$INSTALL_DIR/bin:$PATH"

# 2. Clone OpenE906 at the pinned commit
git init "$INSTALL_DIR/opene906"
(
  cd "$INSTALL_DIR/opene906"
  git remote add origin "$E906_REPO"
  git fetch --depth 1 origin "$E906_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Patch the SoC testbench under smart_run/logical for ACT; the core RTL under
#    E906_RTL_FACTORY is not touched.
#    tb/tb.v:
#      1. Loads one image, mem.pat, into the instruction-bus SRAM.  The vendor loader
#         fills only the first 256 KB from case.pat and clears the data-bus SRAM, which
#         truncates an ACT ELF.
#      2. With +define+ACT_TRACE, prints the PC of every retired instruction (debugging).
#      3. Lets MAX_RUN_TIME and LAST_CYCLE be set on the verilator command line.
#      4. Declares the uart0_sout net, which Verilator rejects as an implicit net.
#      5. Skips the no-retire watchdog on cycle 0, where it fired before reset under
#         Verilator because cycle_count starts at 0 instead of X.
#      The cycle count is also printed when the simulation ends.
#    mem/iahb_mem_ctrl.v:
#      6. Enlarges the instruction-bus SRAM from 256 KB to 1 MB, the smallest
#         instruction-bus window the core supports, so an ACT image and its stack fit.
#         It still answers every access with no wait state.
#    -l (--ignore-whitespace) because the repository's own pre-commit hooks strip the
#    trailing whitespace the vendor file has on several context lines.
patch -p1 -l -d "$INSTALL_DIR/opene906" <<'ACT_E906_TB_PATCH'
--- a/smart_run/logical/tb/tb.v
+++ b/smart_run/logical/tb/tb.v
@@ -35,7 +35,12 @@
 //clock period
 `define CLK_PERIOD          10
 `define TCLK_PERIOD         33
+// ACT patch 3: let the run limits be set on the verilator command line
+// (+define+MAX_RUN_TIME=...), so a hung test fails in seconds instead of after the
+// 70 M cycles the vendor default allows.
+`ifndef MAX_RUN_TIME
 `define MAX_RUN_TIME        700000000
+`endif
 `define clk           tb.clk
 `define rst_b         tb.rst_b
 // `include "../cpu/environment.h"
@@ -54,6 +59,9 @@
 wire jtg_tdo;

 wire uart0_sin;
+// ACT patch 4: declare the UART output.  It was an implicit net, which uart_mnt.v
+// references hierarchically; Verilator rejects that.
+wire uart0_sout;
 wire [7:0]b_pad_gpio_porta;
 static integer FILE;
 //Clock Generator
@@ -105,43 +113,29 @@
 // Memory Initialization
 ///////////////////////////////////////
 integer i;
-reg [31:0] mem_data_size;
-reg [31:0] mem_inst_size;

-reg [31:0] mem_inst_temp [65536];
-reg [31:0] mem_data_temp [65536];
+// ACT patch 1: load one image, mem.pat, into the instruction-bus SRAM, which
+// this patch enlarges to 1 MB (262144 words).  The vendor loader fills only the
+// first 256 KB from case.pat and clears the data-bus SRAM, so an ACT ELF, which is
+// linked as one image at address 0, would be truncated.  The core sends loads and
+// stores below 0x2000_0000 to the instruction bus as well as fetches, so code, data
+// and stack all live there.
+reg [31:0] mem_image_temp [262144];

 initial
 begin
   $display("\t******START TO LOAD PROGRAM******\n");
-  $readmemh("./case.pat", mem_inst_temp);
-  $readmemh("./data.pat", mem_data_temp);
-
-
-  for(i=0;i<65536;i=i+1)
-  begin
-    `RTL_IAHBL_MEM.ram0.mem[i][7:0] = ((^mem_inst_temp[i][31:24]) === 1'bx ) ? 8'b0:mem_inst_temp[i][31:24];
-    `RTL_IAHBL_MEM.ram1.mem[i][7:0] = ((^mem_inst_temp[i][23:16]) === 1'bx ) ? 8'b0:mem_inst_temp[i][23:16];
-    `RTL_IAHBL_MEM.ram2.mem[i][7:0] = ((^mem_inst_temp[i][15: 8]) === 1'bx ) ? 8'b0:mem_inst_temp[i][15: 8];
-    `RTL_IAHBL_MEM.ram3.mem[i][7:0] = ((^mem_inst_temp[i][ 7: 0]) === 1'bx ) ? 8'b0:mem_inst_temp[i][ 7: 0];
-  end
-
- for(i=0;i<=65536;i=i+1)
-  begin
-    `RTL_DAHBL_MEM.ram0.mem[i][7:0]  = 8'b0;
-    `RTL_DAHBL_MEM.ram1.mem[i][7:0]  = 8'b0;
-    `RTL_DAHBL_MEM.ram2.mem[i][7:0]  = 8'b0;
-    `RTL_DAHBL_MEM.ram3.mem[i][7:0]  = 8'b0;
-  end
-  for(i=0;i<=65536;i=i+1)
-  begin
-    `RTL_DAHBL_MEM.ram4.mem[i][7:0]  = 8'b0;
-    `RTL_DAHBL_MEM.ram5.mem[i][7:0]  = 8'b0;
-    `RTL_DAHBL_MEM.ram6.mem[i][7:0]  = 8'b0;
-    `RTL_DAHBL_MEM.ram7.mem[i][7:0]  = 8'b0;
+  for(i=0;i<262144;i=i+1)
+    mem_image_temp[i] = 32'b0;
+  $readmemh("mem.pat", mem_image_temp);
+
+  for(i=0;i<262144;i=i+1)
+  begin
+    `RTL_IAHBL_MEM.ram0.mem[i][7:0] = mem_image_temp[i][31:24];
+    `RTL_IAHBL_MEM.ram1.mem[i][7:0] = mem_image_temp[i][23:16];
+    `RTL_IAHBL_MEM.ram2.mem[i][7:0] = mem_image_temp[i][15: 8];
+    `RTL_IAHBL_MEM.ram3.mem[i][7:0] = mem_image_temp[i][ 7: 0];
   end
-
-
 end
 ///////////////////////////////////////
 // Finish Condition Control
@@ -162,7 +156,9 @@
 // No instrunction retired in the last `LAST_CYCLE cycles
 reg [31:0] retire_inst_in_period;
 reg [31:0] cycle_count;
+`ifndef LAST_CYCLE
 `define LAST_CYCLE 5000
+`endif
 always @(posedge clk or negedge rst_b)
 begin
   if(!rst_b)
@@ -176,7 +172,9 @@
 begin
   if(!rst_b) //reset to zero
     retire_inst_in_period[31:0] <= 32'b0;
-  else if( (cycle_count[31:0] % `LAST_CYCLE) == 0)//check and reset retire_inst_in_period every 50000 cycles
+  // ACT patch 5: skip cycle 0.  Verilator starts cycle_count at 0 rather than X, so
+  // the vendor check fired on the first clock edge, before reset.
+  else if( (cycle_count[31:0] != 0) && (cycle_count[31:0] % `LAST_CYCLE) == 0)//check and reset retire_inst_in_period every 50000 cycles
   begin
     if(retire_inst_in_period[31:0] == 0)begin
       $display("*************************************************************");
@@ -217,6 +215,7 @@
   begin
    $display("\n**********************************************");
    $display("*    simulation finished successfully        *");
+   $display("*    cycle_count = %0d", cycle_count);
    $display("**********************************************");
   #10;
    FILE = $fopen("run_case.report","w");
@@ -231,6 +230,7 @@
   begin
    $display("**********************************************");
    $display("*    simulation finished with error          *");
+   $display("*    cycle_count = %0d", cycle_count);
    $display("**********************************************");
   #10;
    FILE = $fopen("run_case.report","w");
@@ -265,6 +265,15 @@
 end
 `endif

+// ACT patch 2: with +define+ACT_TRACE, print the PC of every retired instruction.
+`ifdef ACT_TRACE
+always @(posedge clk)
+begin
+  if(`SOC_TOP.x_cpu_sub_system_ahb.biu_pad_retire)
+    $display("ACT-RETIRE %0d %08h", cycle_count, `SOC_TOP.x_cpu_sub_system_ahb.biu_pad_retire_pc[31:0]);
+end
+`endif
+
 //Monitor
 `ifndef NO_MONITOR
 mnt x_mnt();
--- a/smart_run/logical/mem/iahb_mem_ctrl.v
+++ b/smart_run/logical/mem/iahb_mem_ctrl.v
@@ -42,7 +42,7 @@
 output  [1 :0]  mmc_lite_hresp;

 // &Regs; @23
-reg     [15:0]  addr_holding;
+reg     [17:0]  addr_holding;                  // ACT patch 6: was [15:0]
 reg     [3 :0]  lite_mem_wen;
 reg             lite_read_bypass;
 reg             lite_read_bypass_vld;
@@ -89,11 +89,12 @@
 wire    [7 :0]  ram2_dout;
 wire    [7 :0]  ram3_din;
 wire    [7 :0]  ram3_dout;
-wire    [15:0]  ram_addr;
+wire    [17:0]  ram_addr;                      // ACT patch 6: was [15:0]
 wire            ram_clk;
 wire    [3 :0]  ram_wen;

-parameter IMEM_WIDTH = 18;
+// ACT patch 6: 1 MB (was 18, 256 KB), so an ACT image with its stack fits.
+parameter IMEM_WIDTH = 20;

 // &Force("nonport","lite_mem_addr"); @27
 // &Force("nonport","lite_mem_cen"); @28
ACT_E906_TB_PATCH

# 4. Verilate.
#
#    The vendor smart_run/Makefile supports only iverilog, VCS and irun, so the verilate
#    step is spelled out here.  The testbench uses delays, wait and force, so it needs
#    --timing.  sim.fl names the RTL through ${CODE_BASE_PATH} and the testbench
#    relative to smart_run/work.
#
#    NO_MONITOR drops mnt.v, which writes every retired instruction and the whole register
#    file to a log.  MAX_RUN_TIME caps a runaway test at 20 M cycles (10 ns each).
mkdir -p "$INSTALL_DIR/opene906/smart_run/work"
(
  cd "$INSTALL_DIR/opene906/smart_run/work"
  export CODE_BASE_PATH="$INSTALL_DIR/opene906/E906_RTL_FACTORY"
  verilator --timing --binary -j "$JOBS" -Wno-fatal -Wno-lint -Wno-style --top-module tb \
    -f ../logical/filelists/sim.fl \
    +define+NO_DUMP +define+NO_MONITOR +define+MAX_RUN_TIME=200000000 -o Vtb
)

# 5. Install the testbench and the per-test runner
install -m 0755 "$INSTALL_DIR/opene906/smart_run/work/obj_dir/Vtb" "$INSTALL_DIR/bin/Vtb"
install -m 0755 "$(dirname "$0")/run-e90x.sh" "$INSTALL_DIR/bin/run-e90x.sh"
