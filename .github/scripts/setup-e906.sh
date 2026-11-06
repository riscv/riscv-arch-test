#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
#
# Patch the OpenE906 smart_run testbench for ACT and export the environment the runner needs.
#
# Usage: setup-e906.sh <install-dir> [--patch-only]
#
# The patch changes only the SoC testbench under smart_run/logical; the core RTL under
# E906_RTL_FACTORY is not touched.
#   tb/tb.v:
#     1. Loads one image, mem.pat, into the instruction-bus SRAM.  The vendor loader
#        fills only the first 256 KB from case.pat and clears the data-bus SRAM, which
#        truncates an ACT ELF.
#     2. With +define+ACT_TRACE, prints the PC of every retired instruction (debugging).
#     3. Lets MAX_RUN_TIME and LAST_CYCLE be set on the verilator command line.
#     4. Declares the uart0_sout net, which Verilator rejects as an implicit net.
#     5. Skips the no-retire watchdog on cycle 0, where it fired before reset under
#        Verilator because cycle_count starts at 0 instead of X.
#     The cycle count is also printed when the simulation ends.
#   mem/iahb_mem_ctrl.v:
#     6. Enlarges the instruction-bus SRAM from 256 KB to 1 MB, the smallest
#        instruction-bus window the core supports, so an ACT image and its stack fit.
#        It still answers every access with no wait state.
#
# Applying the patch is idempotent, so a cached, already patched tree is fine.

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-e906.sh <install-dir> [--patch-only]}"
PATCH_ONLY=0
[ "${2:-}" = "--patch-only" ] && PATCH_ONLY=1

E906_SRC="$INSTALL_DIR/opene906"
TB="$E906_SRC/smart_run/logical/tb/tb.v"

if [ -f "$TB" ]; then
  if grep -q "ACT patch 1" "$TB"; then
    echo "setup-e906.sh: testbench already patched"
  else
    # -l (--ignore-whitespace) because the repository's own pre-commit hooks strip the
    # trailing whitespace the vendor files have on several context lines.
    patch -p1 -l -d "$E906_SRC" <<'ACT_E906_TB_PATCH'
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
+// setup-e906.sh enlarges to 1 MB (262144 words).  The vendor loader fills only the
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
    echo "setup-e906.sh: testbench patched"
  fi
else
  echo "setup-e906.sh: no testbench at $TB" >&2
  exit 2
fi

[ "$PATCH_ONLY" -eq 1 ] && exit 0

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "E906_SNAPSHOT=$E906_SRC/smart_run/work" >>"$GITHUB_ENV"
