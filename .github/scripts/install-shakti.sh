#!/usr/bin/env bash
# Copyright (c) 2026, Harvey Mudd College
# SPDX-License-Identifier: Apache-2.0
# Build the Shakti E-class and C-class Verilator testbenches for CI.
# Usage: install-shakti.sh <install-dir>
# Env:   BSC_PLATFORM  bsc release tarball platform (default: ubuntu-24.04; e.g. rockylinux-9.5)
#        BSC_SHA256    its SHA-256 (known for ubuntu-24.04; otherwise unchecked if unset)
# Cache key derives from sha256(this file); bump the pins below to invalidate.

set -euo pipefail

INSTALL_DIR="${1:?Usage: install-shakti.sh <install-dir>}"
INSTALL_DIR="$(mkdir -p "$INSTALL_DIR" && cd "$INSTALL_DIR" && pwd)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JOBS="${JOBS:-$(nproc)}"

VERILATOR_VERSION="v5.052"
# bsc 2026.07.1 fails on E-class with an internal error ("APath.aPaths': nodes not in graph").
BSC_VERSION="2025.01.1"
BSC_PLATFORM="${BSC_PLATFORM:-ubuntu-24.04}"
if [ "$BSC_PLATFORM" = ubuntu-24.04 ]; then
  BSC_SHA256="${BSC_SHA256:-a85bf49adf1ed6c3d0dd80e619b83e8477d520612d6dd3045eabd95e8ceb28d3}"
fi
BSC_SHA256="${BSC_SHA256:-}"

GITLAB="https://gitlab.com/shaktiproject"
ECLASS_COMMIT="e8a0dfd2d1c4907c74fb58432e379016871fdd3a" # master, release 1.10.2
# base-sim/manager.sh lists these dependencies by branch or tag; pinned to the commits they
# named on 2026-11-01.
ECLASS_DEPS=(
  "common_bsv     $GITLAB/common_bsv.git             42d7768ec81abf7f657ec8302a6ff5a0584ace22" # master
  "devices        $GITLAB/uncore/devices.git         c622ad128b81fc74f7a2365241d51488f7b9dd72" # 5.0.2
  "fabrics        $GITLAB/uncore/fabrics.git         c3d6da4c515886ebe0462995aa0624090dbef85d" # 1.2.0
  "common_verilog $GITLAB/common_verilog.git         029a15059798d5400d0821934f2f36e192b92d01" # master
)

CCLASS_COMMIT="f52775317b0e6c16272f5c42d3dd7d52282f0e65" # master, release 6.1.0 (2026-11-02)
# test_soc/c64_c32/c64_deps.yaml lists these dependencies by tag; pinned to the commits of those tags.
CCLASS_DEPS=(
  "caches_mmu     $GITLAB/uncore/caches_mmu.git      787102aba7af7afeff0755a7bf8ddbfb86ea936b" # 14.6.2
  "common_bsv     $GITLAB/common_bsv.git             42d7768ec81abf7f657ec8302a6ff5a0584ace22" # 3.2.0
  "devices        $GITLAB/uncore/devices.git         60d9dee9090f0015ccd14de47dd09277c3d608a7" # 9.0.8
  "fabrics        $GITLAB/uncore/fabrics.git         c7b2bf7600fc157f327dce29ec0636756fe3e3f0" # 1.3.8
  "common_verilog $GITLAB/common_verilog.git         029a15059798d5400d0821934f2f36e192b92d01" # 3.2.0
  "csrbox         $GITLAB/cores/csrbox.git           d9cedf03e2454f4cbd6b492f5d132f8540483ddc" # 1.12.0
  "riscv-config   $GITLAB/cores/riscv-config.git     70206502f6bb110bd894afd80ee1fd4d24a71076" # 3.8.0
)
# requirements.txt names soc_config 3.0.4; the rest are its dependencies.
SOC_CONFIG="git+$GITLAB/cores/soc_config.git@7d5beeb60a48fecf84aa1043a158991d5203011e" # 3.0.4
# setuptools: soc_config installs csrbox and riscv-config with `pip install . --no-build-isolation`, and
# venvs of Python 3.12 and later no longer include setuptools.
PY_PINS=(Cerberus==1.3.8 ruamel.yaml==0.19.1 pytz==2026.6 GitPython==3.2.1 setuptools==80.9.0)
# soc_config decodes pip's captured stdout as ASCII, including successful installs.
export PIP_PROGRESS_BAR=off

mkdir -p "$INSTALL_DIR/bin"

# Clone <url> at <commit> into <dir>.
fetch() {
  git init -q "$3"
  git -C "$3" remote add origin "$1"
  git -C "$3" fetch -q --depth 1 origin "$2"
  git -C "$3" checkout -q FETCH_HEAD
}

# Replace the regular expression <from> with <to> in <file>, and fail if nothing matched.
patch_line() {
  grep -q -e "$2" "$1" || {
    echo "install-shakti.sh: '$2' not found in $1" >&2
    exit 1
  }
  sed -i "s|$2|$3|" "$1"
}

# 1. Verilator from source
if [ ! -x "$INSTALL_DIR/bin/verilator" ]; then
  git clone -q --depth 1 --branch "$VERILATOR_VERSION" https://github.com/verilator/verilator.git "$INSTALL_DIR/verilator-src"
  (
    cd "$INSTALL_DIR/verilator-src"
    autoconf
    ./configure --prefix="$INSTALL_DIR"
    make -j"$JOBS"
    make install
  )
  rm -rf "$INSTALL_DIR/verilator-src"
fi
export PATH="$INSTALL_DIR/bin:$PATH"

# 2. The Bluespec compiler, from its release tarball
BSC_TAR="bsc-$BSC_VERSION-$BSC_PLATFORM.tar.gz"
BSC_URL="https://github.com/B-Lang-org/bsc/releases/download/$BSC_VERSION"
if [ ! -x "$INSTALL_DIR/bsc/bin/bsc" ]; then
  curl -fsSL -o "$INSTALL_DIR/$BSC_TAR" "$BSC_URL/$BSC_TAR"
  if [ -n "$BSC_SHA256" ]; then
    echo "$BSC_SHA256  $INSTALL_DIR/$BSC_TAR" | sha256sum -c -
  else
    echo "install-shakti.sh: no BSC_SHA256 for $BSC_TAR; not checking it" >&2
  fi
  mkdir -p "$INSTALL_DIR/bsc"
  tar -xzf "$INSTALL_DIR/$BSC_TAR" -C "$INSTALL_DIR/bsc" --strip-components 1
  rm "$INSTALL_DIR/$BSC_TAR"
fi
export PATH="$INSTALL_DIR/bsc/bin:$PATH"
export BLUESPECDIR="$INSTALL_DIR/bsc/lib"

# 3. E-class in its base-sim SoC
ECLASS="$INSTALL_DIR/e-class"
rm -rf "$ECLASS"
fetch "$GITLAB/cores/e-class.git" "$ECLASS_COMMIT" "$ECLASS"
for dep in "${ECLASS_DEPS[@]}"; do
  read -r name url commit <<<"$dep"
  fetch "$url" "$commit" "$ECLASS/base-sim/$name"
done
# Add independent byte controls for the testbench's external interrupt inputs.
patch -p1 -l -d "$ECLASS" <<'ACT_ECLASS_INTERRUPTS'
--- a/base-sim/sign_dump.bsv
+++ b/base-sim/sign_dump.bsv
@@ -49,9 +49,11 @@
     interface AXI4_Master_IFC#(`paddr, XLEN, USERSPACE) master;
     interface AXI4_Slave_IFC#(`paddr, XLEN, USERSPACE) slave;
     method Bool mv_end_simulation;
+    method Bit#(2) mv_ext_interrupts;
   endinterface
   (*synthesize*)
   module mksign_dump_axi4(Ifc_sign_dump_axi4);
+    Reg#(Bit#(2)) rg_ext_interrupts <- mkRegA(0);
     let word_count = 128/valueOf(XLEN);

     Reg#(Bool) rg_start<- mkRegA(False);
@@ -85,9 +87,20 @@
     rule configure_registers(!rg_start);
       let aw <- pop_o (s_xactor.o_wr_addr);
       let w  <- pop_o (s_xactor.o_wr_data);
+      Bit#(TLog#(TDiv#(XLEN, 8))) byte_offset = truncate(aw.awaddr);
+      let write_data = w.wdata >> {byte_offset, 3'b0};
       let b = AXI4_Wr_Resp {bresp: AXI4_SLVERR, buser: aw.awuser, bid:aw.awid};
       if (aw.awaddr[3:0]=='h0) begin
         rg_start_address<=truncate(w.wdata);
+        b.bresp=AXI4_OKAY;
+      end
+      // ACT interrupt controls: byte 4 drives MEIP, byte 5 drives SEIP.
+      else if (aw.awaddr[3:0]=='h4) begin
+        rg_ext_interrupts <= {rg_ext_interrupts[1], write_data[0]};
+        b.bresp=AXI4_OKAY;
+      end
+      else if (aw.awaddr[3:0]=='h5) begin
+        rg_ext_interrupts <= {write_data[0], rg_ext_interrupts[0]};
         b.bresp=AXI4_OKAY;
       end
       else if (aw.awaddr[3:0]=='h8) begin
@@ -129,6 +142,7 @@
       if(rg_total_count==1)
         rg_start<=False;
     endrule
+    method mv_ext_interrupts = rg_ext_interrupts;
     interface master=m_xactor.axi_side;
     interface slave=s_xactor.axi_side;
     method mv_end_simulation = rg_end_sim[1];
@@ -138,10 +152,12 @@
     interface AXI4_Lite_Master_IFC#(`paddr, XLEN, USERSPACE) master;
     interface AXI4_Lite_Slave_IFC#(`paddr, XLEN, USERSPACE) slave;
     method Bool mv_end_simulation;
+    method Bit#(2) mv_ext_interrupts;
   endinterface

   (*synthesize*)
   module mksign_dump_axi4lite(Ifc_sign_dump_axi4lite);
+    Reg#(Bit#(2)) rg_ext_interrupts <- mkRegA(0);
     let word_count = 128/valueOf(XLEN);

     Reg#(Bool) rg_start<- mkRegA(False);
@@ -175,9 +191,20 @@
     rule configure_registers(!rg_start);
       let aw <- pop_o (s_xactor.o_wr_addr);
       let w  <- pop_o (s_xactor.o_wr_data);
+      Bit#(TLog#(TDiv#(XLEN, 8))) byte_offset = truncate(aw.awaddr);
+      let write_data = w.wdata >> {byte_offset, 3'b0};
       let b = AXI4_Lite_Wr_Resp {bresp: AXI4_LITE_SLVERR, buser: aw.awuser};
       if (aw.awaddr[3:0]=='h0) begin
         rg_start_address<=truncate(w.wdata);
+        b.bresp=AXI4_LITE_OKAY;
+      end
+      // ACT interrupt controls: byte 4 drives MEIP, byte 5 drives SEIP.
+      else if (aw.awaddr[3:0]=='h4) begin
+        rg_ext_interrupts <= {rg_ext_interrupts[1], write_data[0]};
+        b.bresp=AXI4_LITE_OKAY;
+      end
+      else if (aw.awaddr[3:0]=='h5) begin
+        rg_ext_interrupts <= {write_data[0], rg_ext_interrupts[0]};
         b.bresp=AXI4_LITE_OKAY;
       end
       else if (aw.awaddr[3:0]=='h8) begin
@@ -219,6 +246,7 @@
       if(rg_total_count==1)
         rg_start<=False;
     endrule
+    method mv_ext_interrupts = rg_ext_interrupts;
     interface master=m_xactor.axi_side;
     interface slave=s_xactor.axi_side;
     method mv_end_simulation = rg_end_sim[1];
--- a/base-sim/Soc.bsv
+++ b/base-sim/Soc.bsv
@@ -248,6 +248,9 @@
     mkConnection(eclass.sb_clint_msip,clint.sb_clint_msip);
     mkConnection(eclass.sb_clint_mtip,clint.sb_clint_mtip);
     mkConnection(eclass.sb_clint_mtime,clint.sb_clint_mtime);
+    rule rl_connect_external_interrupt;
+      eclass.sb_ext_interrupt.put(signature.mv_ext_interrupts[0]);
+    endrule

     `ifdef rtldump
       interface io_dump= eclass.io_dump;
ACT_ECLASS_INTERRUPTS
(
  cd "$ECLASS/base-sim"
  # Build with the open-source bsc and Verilator 5, as on the upstream fix branch for
  # https://gitlab.com/shaktiproject/cores/e-class/-/issues/94 (commit 82dbf50): a smaller
  # GHC stack limit, no basicinout Verilog filter (the open-source bsc does not ship it), and
  # --no-timing. Also drop -static, which needs a static libm, and silence Verilator 5.052's
  # MULTIDRIVEN warning on the asynchronous reset in bsc's FIFOL1.v.
  patch_line Makefile '+RTS -K40000M -RTS' '+RTS -K4000M -RTS'
  # shellcheck disable=SC2016 # a literal ${BLUESPECDIR} in the Makefile
  patch_line Makefile '^  VERILOG_FILTER:= -verilog-filter \${BLUESPECDIR}/bin/basicinout$' '  VERILOG_FILTER:='
  patch_line Makefile '--stats -O3' '--stats --no-timing -O3'
  patch_line Makefile '-Wno-lint' '-Wno-lint -Wno-MULTIDRIVEN'
  patch_line Makefile ' -LDFLAGS "-static"' ''

  # Start from templates/rv32imac.inc and change only these settings:
  #   USERTRAPS=disable  user-level interrupts (the withdrawn N extension), which neither UDB
  #                      nor Sail models.
  #   RESETPC            start at the base of RAM, where the test is loaded, rather than in
  #                      the boot ROM, whose image needs the device-tree tooling.
  #   RTLDUMP=disable    the instruction trace, which also sets misa.S and clears misa.N so
  #                      that misa matches Spike's (src/core/csrfile.bsv lines 241-250).
  #   TRIGGERS=0         the debug triggers. UDB does not claim Sdtrig.
  #   COUNTERS=0         the one event counter, so mhpmcounter3..31 and mhpmevent3..31 read 0.
  #   PMPSIZE=16         16 PMP entries, the most E-class supports, instead of 4. ACT needs
  #                      at least 8 (tests/env/check_defines.h).
  cp templates/rv32imac.inc act.inc
  set_param() {
    patch_line act.inc "^$1=.*" "$1=$2"
  }
  set_param USERTRAPS disable
  set_param RESETPC 2147483648
  set_param RTLDUMP disable
  set_param TRIGGERS 0
  set_param COUNTERS 0
  set_param PMPSIZE 16
  make CONFIG=act.inc generate_verilog
  make CONFIG=act.inc link_verilator
)
install -m 0755 "$ECLASS/base-sim/bin/out" "$INSTALL_DIR/bin/shakti-eclass-sim"

# 4. C-class in its test_soc SoC (sample_config/c64, RV64GC with S and U modes)
CCLASS="$INSTALL_DIR/c-class"
rm -rf "$CCLASS"
fetch "$GITLAB/cores/c-class.git" "$CCLASS_COMMIT" "$CCLASS"
for dep in "${CCLASS_DEPS[@]}"; do
  read -r name url commit <<<"$dep"
  fetch "$url" "$commit" "$CCLASS/$name"
done
patch -p1 -l -d "$CCLASS" <<'ACT_CCLASS_INTERRUPTS'
--- a/test_soc/c64_c32/sign_dump.bsv
+++ b/test_soc/c64_c32/sign_dump.bsv
@@ -21,11 +21,13 @@
   interface Ifc_sign_dump;
     interface AXI4_Master_IFC#(`paddr,`axi4_id_width, `buswidth, `USERSPACE) master;
     interface AXI4_Slave_IFC#(`paddr, `axi4_id_width, `buswidth, `USERSPACE) slave;
+    method Bit#(2) mv_ext_interrupts;
   endinterface

   (*synthesize*)
   module mksign_dump(Ifc_sign_dump);

+    Reg#(Bit#(2)) rg_ext_interrupts <- mkRegA(0);
     let word_count = 128/valueOf(`buswidth);

     Reg#(Bool) rg_start<- mkRegA(False);
@@ -59,9 +61,20 @@
     rule configure_registers(!rg_start);
       let aw <- pop_o (s_xactor.o_wr_addr);
       let w  <- pop_o (s_xactor.o_wr_data);
+      Bit#(TLog#(TDiv#(`buswidth, 8))) byte_offset = truncate(aw.awaddr);
+      let write_data = w.wdata >> {byte_offset, 3'b0};
       let b = AXI4_Wr_Resp {bresp: AXI4_SLVERR, buser: aw.awuser, bid:aw.awid};
       if (aw.awaddr[3:0]=='h0) begin
         rg_start_address<=truncate(w.wdata);
+        b.bresp=AXI4_OKAY;
+      end
+      // ACT interrupt controls: byte 4 drives MEIP, byte 5 drives SEIP.
+      else if (aw.awaddr[3:0]=='h4) begin
+        rg_ext_interrupts <= {rg_ext_interrupts[1], write_data[0]};
+        b.bresp=AXI4_OKAY;
+      end
+      else if (aw.awaddr[3:0]=='h5) begin
+        rg_ext_interrupts <= {write_data[0], rg_ext_interrupts[0]};
         b.bresp=AXI4_OKAY;
       end
       else if (aw.awaddr[3:0]=='h8) begin
@@ -105,6 +118,7 @@
       if(rg_total_count==1)
         rg_start<=False;
     endrule
+    method mv_ext_interrupts = rg_ext_interrupts;
     interface master=m_xactor.axi_side;
     interface slave=s_xactor.axi_side;
   endmodule
--- a/test_soc/c64_c32/Soc.bsv
+++ b/test_soc/c64_c32/Soc.bsv
@@ -203,9 +203,9 @@
     /*doc:rule: */
     rule rl_connect_plic;
       for (Integer i = 0; i<`num_harts; i = i + 1) begin
-         ccore[i].sb_plic_meip(0);
+         ccore[i].sb_plic_meip(signature.mv_ext_interrupts[0]);
       `ifdef supervisor
-        ccore[i].sb_plic_seip(0);
+        ccore[i].sb_plic_seip(signature.mv_ext_interrupts[1]);
       `endif
       end
     endrule:rl_connect_plic
ACT_CCLASS_INTERRUPTS
python3 -m venv "$INSTALL_DIR/venv"
"$INSTALL_DIR/venv/bin/pip" install -q "${PY_PINS[@]}" "$SOC_CONFIG"
(
  cd "$CCLASS"
  # soc_config writes benchmarks/Makefile.inc; the benchmarks themselves are not needed.
  mkdir -p benchmarks
  # Start from sample_config/c64 and change only these settings:
  #   reset_pc       start at the base of RAM, where the test is loaded, rather than in the
  #                  boot ROM, whose image needs the device-tree tooling.
  #   PMP entries    8 usable entries instead of 4: pmp4cfg..pmp7cfg and pmpaddr4..7 get the
  #                  same WARL specification as entry 0. ACT needs at least 8
  #                  (tests/env/check_defines.h). csrbox 1.12.0 generates BSV that does not
  #                  compile for RV64 entries 8..15 (it reads them from a pmpcfg1), so those stay
  #                  read-only zero. pmpcfg2 and pmpaddr4..15 join the CSR grouping, so that all
  #                  16 entries' CSRs exist, as the privileged specification requires.
  #   medeleg, mideleg  delegate only what the privileged specification allows: exceptions
  #                  0-9, 12, 13 and 15, and the supervisor interrupts 1, 5 and 9. The sample's
  #                  mask, 0xF7FF for both, also makes reserved bits 10 and 14 of medeleg and the
  #                  machine and reserved interrupt bits of mideleg writable, which UDB rejects.
  #   satp.ASID      8 writable bits as a bitmask. The sample's range 0..0xFF, with illegal writes
  #                  leaving the field unchanged, makes a write of all ones (the privileged
  #                  specification's way to find ASIDLEN) read back as the old ASID.
  cp -r sample_config/c64 act_config
  patch_line act_config/core64.yaml '^reset_pc: 4096$' 'reset_pc: 2147483648'
  "$INSTALL_DIR/venv/bin/python" - act_config <<'PY'
import copy, sys
from ruamel.yaml import YAML
d = sys.argv[1]
yaml = YAML()
yaml.width = 4096
isa = yaml.load(open(f"{d}/rv64i_isa.yaml"))
h = isa["hart0"]
for i in range(4, 8):
    reg = "pmpcfg0"
    cfg = copy.deepcopy(h["pmpcfg0"]["rv64"]["pmp0cfg"])
    legal = cfg["type"]["warl"]
    legal["dependency_fields"] = [f"{reg}::pmp{i}cfg"]
    legal["legal"] = [x.replace("pmp0cfg", f"pmp{i}cfg") for x in legal["legal"]]
    h[reg]["rv64"][f"pmp{i}cfg"] = cfg
    addr = copy.deepcopy(h["pmpaddr0"])
    w = addr["rv64"]["type"]["warl"]
    w["dependency_fields"] = [f"{reg}::pmp{i}cfg"]
    w["legal"] = [x.replace("pmp0cfg", f"pmp{i}cfg").replace("pmpaddr0", f"pmpaddr{i}") for x in w["legal"]]
    h[f"pmpaddr{i}"] = addr
for reg, mask in (("medeleg", "0x000000000000B3FF"), ("mideleg", "0x0000000000000222")):
    legal = h[reg]["rv64"]["type"]["warl"]["legal"]
    assert legal == [f"{reg}[63:0] bitmask [0x000000000000F7FF,0x0000000000000000]"], legal
    legal[0] = f"{reg}[63:0] bitmask [{mask},0x0000000000000000]"
asid = h["satp"]["rv64"]["asid"]["type"]["warl"]["legal"]
assert asid == ["asid[15:0] in [0x0000:0x00FF]"], asid
asid[0] = "asid[15:0] bitmask [0x00FF,0x0000]"
yaml.dump(isa, open(f"{d}/rv64i_isa.yaml", "w"))
grp = open(f"{d}/csr_grouping64.yaml").read()
extra = "".join(f"    - PMPADDR{i}\n" for i in range(4, 16))
grp = grp.replace("    - PMPADDR3\n", "    - PMPADDR3\n    - PMPCFG2\n" + extra, 1)
assert "PMPADDR15" in grp
open(f"{d}/csr_grouping64.yaml", "w").write(grp)
PY
  # soc_config runs pip to install csrbox and riscv-config from their clones.
  export PATH="$INSTALL_DIR/venv/bin:$PATH"
  soc_config -ispec act_config/rv64i_isa.yaml \
    -customspec act_config/rv64i_custom.yaml -cspec act_config/core64.yaml \
    -gspec act_config/csr_grouping64.yaml -dspec act_config/rv64i_debug.yaml --verbose info
  # soc_config counts the 16 pmpaddr CSRs in the grouping, but csrbox gives the core only the
  # 8 writable entries.
  patch_line makefile.inc ' pmpentries=16 ' ' pmpentries=8 '
  # As for E-class: no -static, and no MULTIDRIVEN warning on bsc's FIFOL1.v.
  patch_line makefile.inc ' -LDFLAGS "-static"' ''
  patch_line makefile.inc '-Wno-lint' '-Wno-lint -Wno-MULTIDRIVEN'
  make -j"$JOBS" generate_verilog
  make link_verilator
)
install -m 0755 "$CCLASS/bin/out" "$INSTALL_DIR/bin/shakti-cclass-sim"

install -m 0755 "$SCRIPT_DIR/run-shakti.sh" "$INSTALL_DIR/bin/run-shakti.sh"
