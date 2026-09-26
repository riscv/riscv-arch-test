#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
#
# Patch the OpenC910 testbench for ACT and export the environment the runner needs.
#
# Usage: setup-c910.sh <install-dir> [--patch-only]
#
# The OpenC910 testbench (smart_run/logical/tb/tb_verilator.v) is written for the
# vendor's own bare-metal smoke tests, and three of its properties make it unusable as
# an ACT DUT harness.  All three are fixed here, as one reviewable patch against the
# pinned commit, rather than by carrying a fork:
#
#   1. THE IMAGE LOADER IS CAPPED AT 256 KB AND SPLIT IN TWO.  It stages inst.pat and
#      data.pat into two `bit [31:0] mem_*_temp[65536]` arrays and copies only
#      `i < 32'h4000` sixteen-byte rows of each, so anything past 256 KB of text (or
#      256 KB of data) is DROPPED SILENTLY - no warning, no error, the core simply
#      fetches zeros.  A self-checking ACT ELF is about 275 KB.  The patch merges the
#      two halves into one 4 MB image called mem.pat and raises the copy bound to
#      0x40000 rows.  Verified by linking a 395 KB image whose last function lives at
#      byte offset 0x62AB0 and jumping to it: it executes and halts correctly.
#
#   2. PASS/FAIL IS SNOOPED OFF THE INTEGER WRITE-BACK BUS, NOT OFF MEMORY.  The
#      testbench watches three write-back data buses for 64'h444333222 (pass) and
#      64'h2382348720 (fail).  That is unusable for ACT twice over: any test that
#      legitimately computes 0x444333222 in a register ends the simulation as a PASS,
#      and the fail comparison is buggy - its third disjunct repeats the PASS constant
#      (`value2 == 64'h444333222`), so a failing value arriving on the load write-back
#      bus is scored as a pass.  The patch deletes the three taps and ends the
#      simulation on a store to a magic address instead: 0x01FF_FFE0 = pass,
#      0x01FF_FFD0 = fail.  Those are what RVMODEL_HALT_PASS / RVMODEL_HALT_FAIL write.
#      Both addresses sit in the strongly-ordered device region 0x0100_0000-0x01FF_FFFF
#      (gen_rtl/mmu/rtl/sysmap.h), so the store is never absorbed by the D-cache.
#
#   3. THE EXIT STATUS IS ALWAYS 0.  sim_main1.cpp returns 0 unconditionally, and the
#      verdict only ever appears in a file called run_case.report as the literal text
#      "TEST PASS" or "TEST FAIL".  Rather than patch the C++, run-c910.sh deletes that
#      file before the run and requires both a "TEST PASS" report and an
#      "RVCP-SUMMARY: TEST PASSED" console line; a timeout, a hang or a crash leaves
#      the file absent and fails.  The patch does add one thing here: `ifndef` guards
#      around MAX_RUN_TIME and LAST_CYCLE so the cycle cap can be set at verilate time
#      (install-c910.sh uses 4 M instead of the vendor's 50.3 M).
#
# Applying the patch is idempotent: if it is already applied the script says so and
# succeeds, so a cache restore that already contains a patched tree is fine.

set -euo pipefail

INSTALL_DIR="${1:?Usage: setup-c910.sh <install-dir> [--patch-only]}"
PATCH_ONLY=0
[ "${2:-}" = "--patch-only" ] && PATCH_ONLY=1

C910_SRC="$INSTALL_DIR/openc910"
TB="$C910_SRC/smart_run/logical/tb/tb_verilator.v"

if [ -f "$TB" ]; then
  if grep -q "ACT patch 1" "$TB"; then
    echo "setup-c910.sh: testbench already patched"
  else
    # -l (--ignore-whitespace) because the repository's own pre-commit hooks strip the
    # trailing whitespace the vendor file has on several context lines.
    patch -p1 -l -d "$C910_SRC" <<'ACT_C910_TB_PATCH'
diff --git a/smart_run/logical/tb/tb_verilator.v b/smart_run/logical/tb/tb_verilator.v
index ab4fee5..c191181 100644
--- a/smart_run/logical/tb/tb_verilator.v
+++ b/smart_run/logical/tb/tb_verilator.v
@@ -31,7 +31,12 @@ limitations under the License.

 `define CLK_PERIOD          10
 `define TCLK_PERIOD         40
+// ACT patch 3: make the two run-limit knobs overridable from the verilator command
+// line (+define+MAX_RUN_TIME=...), so a hung test fails in minutes instead of the
+// 50.3 M cycles the vendor default allows.
+`ifndef MAX_RUN_TIME
 `define MAX_RUN_TIME        32'h3000000
+`endif

 `define SOC_TOP             top.x_soc
 `define RTL_MEM             top.x_soc.x_axi_slave128.x_f_spsram_large
@@ -134,8 +139,11 @@ module top(
   end

   integer i;
-  bit [31:0] mem_inst_temp [65536];
-  bit [31:0] mem_data_temp [65536];
+  // ACT patch 1: the vendor loader stages two 65536-word (256 KB) halves and copies
+  // only 0x4000 16-byte rows of each, so any image larger than 256 KB of text or
+  // 256 KB of data is silently truncated.  ACT self-checking ELFs are ~275 KB.
+  // One 4 MB image ("mem.pat") replaces inst.pat + data.pat.
+  bit [31:0] mem_image_temp [1048576];
   integer j;
   initial
   begin
@@ -162,56 +170,31 @@ module top(
     end

     $display("\t********* Read program *********");
-    $readmemh("inst.pat", mem_inst_temp);
-    $readmemh("data.pat", mem_data_temp);
+    $readmemh("mem.pat", mem_image_temp);

     $display("\t********* Load program to memory *********");
     i=0;
-    for(j=0;i<32'h4000;i=j/4)
-    begin
-      `RTL_MEM.ram0.mem[i][7:0] = mem_inst_temp[j][31:24];
-      `RTL_MEM.ram1.mem[i][7:0] = mem_inst_temp[j][23:16];
-      `RTL_MEM.ram2.mem[i][7:0] = mem_inst_temp[j][15: 8];
-      `RTL_MEM.ram3.mem[i][7:0] = mem_inst_temp[j][ 7: 0];
-      j = j+1;
-      `RTL_MEM.ram4.mem[i][7:0] = mem_inst_temp[j][31:24];
-      `RTL_MEM.ram5.mem[i][7:0] = mem_inst_temp[j][23:16];
-      `RTL_MEM.ram6.mem[i][7:0] = mem_inst_temp[j][15: 8];
-      `RTL_MEM.ram7.mem[i][7:0] = mem_inst_temp[j][ 7: 0];
-      j = j+1;
-      `RTL_MEM.ram8.mem[i][7:0] = mem_inst_temp[j][31:24];
-      `RTL_MEM.ram9.mem[i][7:0] = mem_inst_temp[j][23:16];
-      `RTL_MEM.ram10.mem[i][7:0] = mem_inst_temp[j][15: 8];
-      `RTL_MEM.ram11.mem[i][7:0] = mem_inst_temp[j][ 7: 0];
-      j = j+1;
-      `RTL_MEM.ram12.mem[i][7:0] = mem_inst_temp[j][31:24];
-      `RTL_MEM.ram13.mem[i][7:0] = mem_inst_temp[j][23:16];
-      `RTL_MEM.ram14.mem[i][7:0] = mem_inst_temp[j][15: 8];
-      `RTL_MEM.ram15.mem[i][7:0] = mem_inst_temp[j][ 7: 0];
-      j = j+1;
-    end
-    i=0;
-    for(j=0;i<32'h4000;i=j/4)
+    for(j=0;i<32'h40000;i=j/4)
     begin
-      `RTL_MEM.ram0.mem[i+32'h4000][7:0]  = mem_data_temp[j][31:24];
-      `RTL_MEM.ram1.mem[i+32'h4000][7:0]  = mem_data_temp[j][23:16];
-      `RTL_MEM.ram2.mem[i+32'h4000][7:0]  = mem_data_temp[j][15: 8];
-      `RTL_MEM.ram3.mem[i+32'h4000][7:0]  = mem_data_temp[j][ 7: 0];
+      `RTL_MEM.ram0.mem[i][7:0] = mem_image_temp[j][31:24];
+      `RTL_MEM.ram1.mem[i][7:0] = mem_image_temp[j][23:16];
+      `RTL_MEM.ram2.mem[i][7:0] = mem_image_temp[j][15:8];
+      `RTL_MEM.ram3.mem[i][7:0] = mem_image_temp[j][7:0];
       j = j+1;
-      `RTL_MEM.ram4.mem[i+32'h4000][7:0]  = mem_data_temp[j][31:24];
-      `RTL_MEM.ram5.mem[i+32'h4000][7:0]  = mem_data_temp[j][23:16];
-      `RTL_MEM.ram6.mem[i+32'h4000][7:0]  = mem_data_temp[j][15: 8];
-      `RTL_MEM.ram7.mem[i+32'h4000][7:0]  = mem_data_temp[j][ 7: 0];
+      `RTL_MEM.ram4.mem[i][7:0] = mem_image_temp[j][31:24];
+      `RTL_MEM.ram5.mem[i][7:0] = mem_image_temp[j][23:16];
+      `RTL_MEM.ram6.mem[i][7:0] = mem_image_temp[j][15:8];
+      `RTL_MEM.ram7.mem[i][7:0] = mem_image_temp[j][7:0];
       j = j+1;
-      `RTL_MEM.ram8.mem[i+32'h4000][7:0]   = mem_data_temp[j][31:24];
-      `RTL_MEM.ram9.mem[i+32'h4000][7:0]   = mem_data_temp[j][23:16];
-      `RTL_MEM.ram10.mem[i+32'h4000][7:0]  = mem_data_temp[j][15: 8];
-      `RTL_MEM.ram11.mem[i+32'h4000][7:0]  = mem_data_temp[j][ 7: 0];
+      `RTL_MEM.ram8.mem[i][7:0] = mem_image_temp[j][31:24];
+      `RTL_MEM.ram9.mem[i][7:0] = mem_image_temp[j][23:16];
+      `RTL_MEM.ram10.mem[i][7:0] = mem_image_temp[j][15:8];
+      `RTL_MEM.ram11.mem[i][7:0] = mem_image_temp[j][7:0];
       j = j+1;
-      `RTL_MEM.ram12.mem[i+32'h4000][7:0]  = mem_data_temp[j][31:24];
-      `RTL_MEM.ram13.mem[i+32'h4000][7:0]  = mem_data_temp[j][23:16];
-      `RTL_MEM.ram14.mem[i+32'h4000][7:0]  = mem_data_temp[j][15: 8];
-      `RTL_MEM.ram15.mem[i+32'h4000][7:0]  = mem_data_temp[j][ 7: 0];
+      `RTL_MEM.ram12.mem[i][7:0] = mem_image_temp[j][31:24];
+      `RTL_MEM.ram13.mem[i][7:0] = mem_image_temp[j][23:16];
+      `RTL_MEM.ram14.mem[i][7:0] = mem_image_temp[j][15:8];
+      `RTL_MEM.ram15.mem[i][7:0] = mem_image_temp[j][7:0];
       j = j+1;
     end
   end
@@ -243,7 +226,9 @@ module top(
   reg [31:0] retire_inst_in_period;
   reg [31:0] cycle_count;

+  `ifndef LAST_CYCLE
   `define LAST_CYCLE 50000
+  `endif
   always @(posedge clk or negedge rst_b)
   begin
     if(!rst_b)
@@ -282,9 +267,7 @@ module top(
   reg [3:0]  cpu_awlen;
   reg [15:0] cpu_wstrb;
   reg        cpu_wvalid;
-  reg [63:0] value0;
-  reg [63:0] value1;
-  reg [63:0] value2;
+  // ACT patch 2: value0/value1/value2 (taps on the integer write-back bus) deleted.


   always @(posedge clk)
@@ -293,45 +276,40 @@ module top(
     cpu_awaddr[31:0] <= `SOC_TOP.x_axi_slave128.mem_addr[31:0];
     cpu_wvalid       <= `SOC_TOP.biu_pad_wvalid;
     cpu_wstrb        <= `SOC_TOP.biu_pad_wstrb;
-    // value0           <= `CPU_TOP.core0_pad_wb0_data[63:0];
-    // value1           <= `CPU_TOP.core0_pad_wb1_data[63:0];
-    // value2           <= `CPU_TOP.core0_pad_wb2_data[63:0];
-    value0              <= `CPU_TOP.x_ct_top_0.x_ct_core.x_ct_iu_top.x_ct_iu_rbus.rbus_pipe0_wb_data[63:0];
-    value1              <= `CPU_TOP.x_ct_top_0.x_ct_core.x_ct_iu_top.x_ct_iu_rbus.rbus_pipe1_wb_data[63:0];
-    value2              <= `CPU_TOP.x_ct_top_0.x_ct_core.x_ct_lsu_top.x_ct_lsu_ld_wb.ld_wb_preg_data_sign_extend[63:0];
   end

+  // ACT patch 2: the vendor testbench ended the simulation when the integer
+  // write-back bus produced 64'h444333222 (pass) or 64'h2382348720 (fail).  Two
+  // defects: (a) any test that legitimately computes 0x444333222 in a GPR halts the
+  // run as a PASS, and (b) the fail comparison's third disjunct repeated the *pass*
+  // constant (`value2 == 64'h444333222`) so a failing load result was scored PASS.
+  // Replaced by an explicit store to a magic address, which is what ACT's
+  // RVMODEL_HALT_PASS / RVMODEL_HALT_FAIL drive.
+  wire halt_store = (cpu_awlen[3:0] == 4'b0) && cpu_wvalid && `clk_en;
+
   always @(posedge clk)
   begin
-      if(value0 == 64'h444333222 || value1 == 64'h444333222 || value2 == 64'h444333222)
+    if(halt_store && (cpu_awaddr[31:0] == 32'h01ff_ffe0))
     begin
       $display("**********************************************");
       $display("*    simulation finished successfully        *");
+      $display("*    cycle_count = %0d", cycle_count);
       $display("**********************************************");
-     //#10;
-     FILE = $fopen("run_case.report","w");
-     $fwrite(FILE,"TEST PASS");
-
-     $finish;
+      FILE = $fopen("run_case.report","w");
+      $fwrite(FILE,"TEST PASS");
+      $finish;
     end
-      else if (value0 == 64'h2382348720 || value1 == 64'h2382348720 || value2 == 64'h444333222)
+    else if(halt_store && (cpu_awaddr[31:0] == 32'h01ff_ffd0))
     begin
-     $display("**********************************************");
-     $display("*    simulation finished with error          *");
-     $display("**********************************************");
-     //#10;
-     FILE = $fopen("run_case.report","w");
-     $fwrite(FILE,"TEST FAIL");
-
-     $finish;
+      $display("**********************************************");
+      $display("*    simulation finished with error          *");
+      $display("*    cycle_count = %0d", cycle_count);
+      $display("**********************************************");
+      FILE = $fopen("run_case.report","w");
+      $fwrite(FILE,"TEST FAIL");
+      $finish;
     end
-
-    else if((cpu_awlen[3:0] == 4'b0) &&
-  //     (cpu_awaddr[31:0] == 32'h6000fff8) &&
-  //     (cpu_awaddr[31:0] == 32'h0003fff8) &&
-       (cpu_awaddr[31:0] == 32'h01ff_fff0) &&
-        cpu_wvalid &&
-       `clk_en)
+    else if(halt_store && (cpu_awaddr[31:0] == 32'h01ff_fff0))
     begin
      if(cpu_wstrb[15:0] == 16'hf)
      begin
@@ -350,11 +328,8 @@ module top(
         $write("%c", `SOC_TOP.biu_pad_wdata[103:96]);
      end
     end
-
   end
-
-
-
+
   parameter cpu_cycle = 110;
   `ifndef NO_DUMP
   initial
ACT_C910_TB_PATCH
    echo "setup-c910.sh: testbench patched"
  fi
else
  echo "setup-c910.sh: no testbench at $TB" >&2
  exit 2
fi

[ "$PATCH_ONLY" -eq 1 ] && exit 0

echo "$INSTALL_DIR/bin" >>"$GITHUB_PATH"
echo "C910_SNAPSHOT=$C910_SRC/smart_run/work" >>"$GITHUB_ENV"
