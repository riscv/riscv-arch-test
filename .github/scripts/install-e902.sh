#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build a verilated XuanTie OpenE902 smart_run SoC testbench for CI.
# Usage: install-e902.sh <install-dir>
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-e902.sh <install-dir>}"
E902_REPO="https://github.com/T-head-Semi/opene902.git"
E902_COMMIT="991836411b405ac6a0a8d7668f2f5de6fa2a5b8c"
VERILATOR_VERSION="v5.052"

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

# 2. Clone OpenE902 at the pinned commit
git init "$INSTALL_DIR/opene902"
(
  cd "$INSTALL_DIR/opene902"
  git remote add origin "$E902_REPO"
  git fetch --depth 1 origin "$E902_COMMIT"
  git checkout FETCH_HEAD
)

# 3. Patch smart_run/logical/tb/tb.v for ACT.  The patch
#      1. loads one image, mem.pat, into all 512 KB of the instruction-bus SRAM.  The vendor
#         loader fills only 256 KB of it (inst.pat) and loads data.pat into the separate
#         data SRAM, which truncates an ACT ELF;
#      2. prints the cycle count when the simulation ends;
#      3. lets MAX_RUN_TIME and LAST_CYCLE be set on the verilator command line;
#      4. declares the uart0_sout net, which Verilator rejects as an implicit net;
#      5. skips the no-retire watchdog on cycle 0, where it fired before reset under
#         Verilator because cycle_count starts at 0 instead of X.
#    -l (--ignore-whitespace) because the repository's own pre-commit hooks strip the
#    trailing whitespace the vendor file has on several context lines.
patch -p1 -l -d "$INSTALL_DIR/opene902" <<'ACT_E902_TB_PATCH'
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

# 4. Verilate.
#
#    The vendor smart_run/Makefile supports only iverilog, VCS and irun, so the verilate
#    step is spelled out here.  The testbench uses delays, wait and force, so it needs
#    --timing.  The filelists name files relative to smart_run/work.  The RTL filelist
#    ends with a bare directory, ${CODE_BASE_PATH}/gen_rtl, which Verilator would read as
#    a source file, so only its file entries are passed.
#
#    NO_MONITOR drops mnt.v, which writes every retired instruction and the whole register
#    file to GPR.log.  MAX_RUN_TIME caps a runaway test at 20 M cycles (10 ns each).
mkdir -p "$INSTALL_DIR/opene902/smart_run/work"
(
  cd "$INSTALL_DIR/opene902/smart_run/work"
  export CODE_BASE_PATH="$INSTALL_DIR/opene902/E902_RTL_FACTORY"
  sed -n '/gen_rtl\//p' "$CODE_BASE_PATH/gen_rtl/filelists/E902_asic_rtl.fl" >e902_rtl.fl
  verilator --timing --binary -j "$(nproc)" -Wno-fatal -Wno-lint -Wno-style --top-module tb \
    -f e902_rtl.fl -f ../logical/filelists/smart.fl -f ../logical/filelists/tb.fl \
    +define+NO_DUMP +define+NO_MONITOR +define+MAX_RUN_TIME=200000000 -o Vtb
)

# 5. Install the testbench and the per-test runner
install -m 0755 "$INSTALL_DIR/opene902/smart_run/work/obj_dir/Vtb" "$INSTALL_DIR/bin/Vtb"
install -m 0755 "$(dirname "$0")/run-e90x.sh" "$INSTALL_DIR/bin/run-e90x.sh"
