#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
#
# Patch the OpenE902 smart_run testbench for ACT and export the environment the runner needs.
#
# Usage: setup-e902.sh <install-dir> [--patch-only]
#
# The patch to smart_run/logical/tb/tb.v:
#   1. Loads one image, mem.pat, into all 512 KB of the instruction-bus SRAM.  The vendor
#      loader fills only 256 KB of it (inst.pat) and loads data.pat into the separate
#      data SRAM, which truncates an ACT ELF.
#   2. Prints the cycle count when the simulation ends.
#   3. Lets MAX_RUN_TIME and LAST_CYCLE be set on the verilator command line.
#   4. Declares the uart0_sout net, which Verilator rejects as an implicit net.
#   5. Skips the no-retire watchdog on cycle 0, where it fired before reset under
#      Verilator because cycle_count starts at 0 instead of X.
#
# Applying the patch is idempotent, so a cached, already patched tree is fine.

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-e902.sh <install-dir> [--patch-only]}"
PATCH_ONLY=0
[ "${2:-}" = "--patch-only" ] && PATCH_ONLY=1

E902_SRC="$INSTALL_DIR/opene902"
TB="$E902_SRC/smart_run/logical/tb/tb.v"

if [ -f "$TB" ]; then
  if grep -q "ACT patch 1" "$TB"; then
    echo "setup-e902.sh: testbench already patched"
  else
    # -l (--ignore-whitespace) because the repository's own pre-commit hooks strip the
    # trailing whitespace the vendor file has on several context lines.
    patch -p1 -l -d "$E902_SRC" <<'ACT_E902_TB_PATCH'
--- a/smart_run/logical/tb/tb.v
+++ b/smart_run/logical/tb/tb.v
@@ -25,7 +25,12 @@
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

@@ -46,6 +51,9 @@
 wire jtg_tdo;

 wire uart0_sin;
+// ACT patch 4: declare the UART output.  It was an implicit net, which uart_mnt.v
+// references hierarchically; Verilator rejects that.
+wire uart0_sout;
 wire [7:0]b_pad_gpio_porta;
 static integer FILE;
 //Clock Generator
@@ -89,39 +97,30 @@
 // Memory Initialization
 ///////////////////////////////////////
 integer i;
-reg [31:0] mem_data_size;
-reg [31:0] mem_inst_size;

-reg [31:0] mem_inst_temp [65536];
-reg [31:0] mem_data_temp [65536];
+// ACT patch 1: load one image, mem.pat, into all 512 KB of the instruction-bus SRAM.
+// The vendor loader fills only the first 256 KB (65536 words) from inst.pat and
+// loads data.pat into the system-bus data SRAM at 0x2000_0000, so an ACT ELF, which
+// is linked as one image and can exceed 256 KB, would be silently truncated.
+// Instruction-bus SRAM is 2^IMEM_WIDTH bytes, IMEM_WIDTH = 19
+// (../mem/iahb_mem_ctrl.v), and the core sends loads and stores below 0x2000_0000
+// to it as well as fetches, so code, data and stack all live there.
+reg [31:0] mem_image_temp [131072];

 initial
 begin
   $display("\t******START TO LOAD PROGRAM******\n");
-  $readmemh("inst.pat", mem_inst_temp);
-  $readmemh("data.pat", mem_data_temp);
-
+  for(i=0;i<131072;i=i+1)
+    mem_image_temp[i] = 32'b0;
+  $readmemh("mem.pat", mem_image_temp);

-  for(i=0;i<65536;i=i+1)
+  for(i=0;i<131072;i=i+1)
   begin
-    `RTL_IAHBL_MEM.ram0.mem[i][7:0] = ((^mem_inst_temp[i][31:24]) === 1'bx ) ? 8'b0:mem_inst_temp[i][31:24];
-    `RTL_IAHBL_MEM.ram1.mem[i][7:0] = ((^mem_inst_temp[i][23:16]) === 1'bx ) ? 8'b0:mem_inst_temp[i][23:16];
-    `RTL_IAHBL_MEM.ram2.mem[i][7:0] = ((^mem_inst_temp[i][15: 8]) === 1'bx ) ? 8'b0:mem_inst_temp[i][15: 8];
-    `RTL_IAHBL_MEM.ram3.mem[i][7:0] = ((^mem_inst_temp[i][ 7: 0]) === 1'bx ) ? 8'b0:mem_inst_temp[i][ 7: 0];
+    `RTL_IAHBL_MEM.ram0.mem[i][7:0] = mem_image_temp[i][31:24];
+    `RTL_IAHBL_MEM.ram1.mem[i][7:0] = mem_image_temp[i][23:16];
+    `RTL_IAHBL_MEM.ram2.mem[i][7:0] = mem_image_temp[i][15: 8];
+    `RTL_IAHBL_MEM.ram3.mem[i][7:0] = mem_image_temp[i][ 7: 0];
   end
-
-
-
- for(i=0;i<65536;i=i+1)
-  begin
-    `RTL_DAHBL_MEM.ram0.mem[i][7:0]  = ((^mem_data_temp[i][31:24]) === 1'bx ) ? 8'b0:mem_data_temp[i][31:24];
-    `RTL_DAHBL_MEM.ram1.mem[i][7:0]  = ((^mem_data_temp[i][23:16]) === 1'bx ) ? 8'b0:mem_data_temp[i][23:16];
-    `RTL_DAHBL_MEM.ram2.mem[i][7:0]  = ((^mem_data_temp[i][15: 8]) === 1'bx ) ? 8'b0:mem_data_temp[i][15: 8];
-    `RTL_DAHBL_MEM.ram3.mem[i][7:0]  = ((^mem_data_temp[i][ 7: 0]) === 1'bx ) ? 8'b0:mem_data_temp[i][ 7: 0];
-  end
-
-
-
 end
 ///////////////////////////////////////
 // Finish Condition Control
@@ -141,7 +140,9 @@
 // No instrunction retired in the last `LAST_CYCLE cycles
 reg [31:0] retire_inst_in_period;
 reg [31:0] cycle_count;
+`ifndef LAST_CYCLE
 `define LAST_CYCLE 5000
+`endif
 always @(posedge clk or negedge rst_b)
 begin
   if(!rst_b)
@@ -155,7 +156,9 @@
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
@@ -196,6 +199,7 @@
   begin
    $display("\n**********************************************");
    $display("*    simulation finished successfully        *");
+   $display("*    cycle_count = %0d", cycle_count);
    $display("**********************************************");
   #10;
    FILE = $fopen("run_case.report","w");
@@ -210,6 +214,7 @@
   begin
    $display("**********************************************");
    $display("*    simulation finished with error          *");
+   $display("*    cycle_count = %0d", cycle_count);
    $display("**********************************************");
   #10;
    FILE = $fopen("run_case.report","w");
ACT_E902_TB_PATCH
    echo "setup-e902.sh: testbench patched"
  fi
else
  echo "setup-e902.sh: no testbench at $TB" >&2
  exit 2
fi

[ "$PATCH_ONLY" -eq 1 ] && exit 0

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "E902_SNAPSHOT=$E902_SRC/smart_run/work" >>"$GITHUB_ENV"
