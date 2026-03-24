//
// Copyright (c) 2023 Imperas Software Ltd., www.imperas.com
// Modified February 2024, jcarlin@hmc.edu
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.0
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
// either express or implied.
//
// See the License for the specific language governing permissions and
// limitations under the License.
//
//

typedef enum {
  dcsr,
  etrigger,
  fcsr,
  fflags,
  frm,
  hcounteren,
  hedeleg,
  hgatp,
  hgeie,
  hgeip,
  hideleg,
  hie,
  hip,
  hstatus,
  hvip,
  icount,
  itrigger,
  jvt,
  mcause,
  mcontrol,
  mcounteren,
  mcountinhibit,
  medeleg,
  mideleg,
  mie,
  mip,
  misa,
  mseccfg,
  mstatus,
  mstatush,
  mtvec,
  pmpcfg0,
  pmpcfg1,
  pmpcfg2,
  pmpcfg3,
  satp,
  scause,
  scounteren,
  seed,
  sie,
  sip,
  sstatus,
  stvec,
  tcontrol,
  tdata1,
  textra32,
  textra64,
  tinfo,
  vcsr,
  vl,
  vlenb,
  vsatp,
  vscause,
  vsie,
  vsip,
  vsstatus,
  vstart,
  vstvec,
  vtype,
  vxrm,
  vxsat
} csr_name_t;

function `XLEN_BITS get_csr_val(int hart, int issue, int prev, string name, string field);
  int addr = get_csr_addr(hart, name);
  return get_csr_val_addr(hart, issue, prev, addr, name, field);
endfunction

function `XLEN_BITS get_csr_val_addr(int hart, int issue, int prev, int addr, string name, string field);

  `XLEN_BITS val;
  val = traceDataQ[hart][issue][prev].csr[addr];

  // If the field is defined/found, shift and mask the value to be returned
  if (name == "dcsr") begin
    case(field)
      "cause" : val = (val >> 6) & 'h7;
      "ebreakm" : val = (val >> 15) & 'h1;
      "ebreaks" : val = (val >> 13) & 'h1;
      "ebreaku" : val = (val >> 12) & 'h1;
      "mprven" : val = (val >> 4) & 'h1;
      "nmip" : val = (val >> 3) & 'h1;
      "prv" : val = val & 'h3;
      "step" : val = (val >> 2) & 'h1;
      "stepie" : val = (val >> 11) & 'h1;
      "stopcount" : val = (val >> 10) & 'h1;
      "stoptime" : val = (val >> 9) & 'h1;
      "xdebugver" : val = (val >> 28) & 'hf;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "etrigger") begin
    case(field)
`ifdef XLEN32
      "dmode" : val = (val >> 27) & 32'h1;
`endif
`ifdef XLEN64
      "dmode" : val = (val >> 59) & 64'h1;
`endif
`ifdef XLEN32
      "hit" : val = (val >> 26) & 32'h1;
`endif
`ifdef XLEN64
      "hit" : val = (val >> 58) & 64'h1;
`endif
      "m" : val = (val >> 9) & 'h1;
      "nmi" : val = (val >> 10) & 'h1;
      "s" : val = (val >> 7) & 'h1;
`ifdef XLEN32
      "type" : val = (val >> 28) & 32'hf;
`endif
`ifdef XLEN64
      "type" : val = (val >> 60) & 64'hf;
`endif
      "u" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "fcsr") begin
    case(field)
      "fflags" : val = val & 'h1f;
      "frm" : val = (val >> 5) & 'h7;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "fflags") begin
    case(field)
      "fflags" : val = val & 'h1f;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "frm") begin
    case(field)
      "frm" : val = val & 'h7;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hcounteren") begin
    case(field)
      "cy" : val = val & 'h1;
      "enable" : val = (val >> 3) & 'h1fffffff;
      "ir" : val = (val >> 2) & 'h1;
      "tm" : val = (val >> 1) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hedeleg") begin
    case(field)
      "deleg" : val = val & 'hffffffff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hgatp") begin
    case(field)
`ifdef XLEN32
      "mode" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN64
      "mode" : val = (val >> 60) & 64'hf;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hgeie") begin
    case(field)
      "enable" : val = (val >> 1) & 'h7fffffff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hgeip") begin
    case(field)
      "pending" : val = (val >> 1) & 'h7fffffff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hideleg") begin
    case(field)
      "meip" : val = (val >> 11) & 'h1;
      "msip" : val = (val >> 3) & 'h1;
      "mtip" : val = (val >> 7) & 'h1;
      "seip" : val = (val >> 9) & 'h1;
      "sgeip" : val = (val >> 12) & 'h1;
      "ssip" : val = (val >> 1) & 'h1;
      "stip" : val = (val >> 5) & 'h1;
      "vgeip" : val = (val >> 10) & 'h1;
      "vssip" : val = (val >> 2) & 'h1;
      "vstip" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hie") begin
    case(field)
      "sgeie" : val = (val >> 12) & 'h1;
      "vseie" : val = (val >> 10) & 'h1;
      "vssie" : val = (val >> 2) & 'h1;
      "vstie" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hip") begin
    case(field)
      "sgeip" : val = (val >> 12) & 'h1;
      "vseip" : val = (val >> 10) & 'h1;
      "vssip" : val = (val >> 2) & 'h1;
      "vstip" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hstatus") begin
    case(field)
      "gva" : val = (val >> 6) & 'h1;
      "hu" : val = (val >> 9) & 'h1;
      "spv" : val = (val >> 7) & 'h1;
      "spvp" : val = (val >> 8) & 'h1;
      "vsbe" : val = (val >> 5) & 'h1;
`ifdef XLEN64
      "vsxl" : val = (val >> 32) & 64'h3;
`endif
      "vtsr" : val = (val >> 22) & 'h1;
      "vtvm" : val = (val >> 20) & 'h1;
      "vtw" : val = (val >> 21) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "hvip") begin
    case(field)
      "vseip" : val = (val >> 10) & 'h1;
      "vssip" : val = (val >> 2) & 'h1;
      "vstip" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "icount") begin
    case(field)
`ifdef XLEN32
      "dmode" : val = (val >> 27) & 32'h1;
`endif
`ifdef XLEN64
      "dmode" : val = (val >> 59) & 64'h1;
`endif
      "hit" : val = (val >> 24) & 'h1;
      "m" : val = (val >> 9) & 'h1;
      "s" : val = (val >> 7) & 'h1;
`ifdef XLEN32
      "type" : val = (val >> 28) & 32'hf;
`endif
`ifdef XLEN64
      "type" : val = (val >> 60) & 64'hf;
`endif
      "u" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "itrigger") begin
    case(field)
`ifdef XLEN32
      "dmode" : val = (val >> 27) & 32'h1;
`endif
`ifdef XLEN64
      "dmode" : val = (val >> 59) & 64'h1;
`endif
`ifdef XLEN32
      "hit" : val = (val >> 26) & 32'h1;
`endif
`ifdef XLEN64
      "hit" : val = (val >> 58) & 64'h1;
`endif
      "m" : val = (val >> 9) & 'h1;
      "s" : val = (val >> 7) & 'h1;
`ifdef XLEN32
      "type" : val = (val >> 28) & 32'hf;
`endif
`ifdef XLEN64
      "type" : val = (val >> 60) & 64'hf;
`endif
      "u" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "jvt") begin
    case(field)
`ifdef XLEN32
      "base" : val = (val >> 6) & 32'h3ffffff;
`endif
`ifdef XLEN64
      "base" : val = (val >> 6) & 64'h3ffffffffffffff;
`endif
      "mode" : val = val & 'h3f;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mcause") begin
    case(field)
`ifdef XLEN32
      "int" : val = val & 32'hffffffff;
`endif
`ifdef XLEN64
      "int" : val = val & 64'hffffffffffffffff;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mcontrol") begin
    case(field)
      "action" : val = (val >> 12) & 'hf;
      "chain" : val = (val >> 11) & 'h1;
`ifdef XLEN32
      "dmode" : val = (val >> 27) & 32'h1;
`endif
`ifdef XLEN64
      "dmode" : val = (val >> 59) & 64'h1;
`endif
      "execute" : val = (val >> 2) & 'h1;
      "hit" : val = (val >> 20) & 'h1;
      "load" : val = val & 'h1;
      "m" : val = (val >> 6) & 'h1;
`ifdef XLEN32
      "maskmax" : val = (val >> 21) & 32'h3f;
`endif
`ifdef XLEN64
      "maskmax" : val = (val >> 53) & 64'h3f;
`endif
      "match" : val = (val >> 7) & 'hf;
      "s" : val = (val >> 4) & 'h1;
      "select" : val = (val >> 19) & 'h1;
`ifdef XLEN64
      "sizehi" : val = (val >> 21) & 64'h3;
`endif
      "sizelo" : val = (val >> 16) & 'h3;
      "store" : val = (val >> 1) & 'h1;
      "timing" : val = (val >> 18) & 'h1;
`ifdef XLEN32
      "type" : val = (val >> 28) & 32'hf;
`endif
`ifdef XLEN64
      "type" : val = (val >> 60) & 64'hf;
`endif
      "u" : val = (val >> 3) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mcounteren") begin
    case(field)
      "cy" : val = val & 'h1;
      "enable" : val = (val >> 3) & 'h1fffffff;
      "ir" : val = (val >> 2) & 'h1;
      "tm" : val = (val >> 1) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mcountinhibit") begin
    case(field)
      "cy" : val = val & 'h1;
      "inhibit" : val = (val >> 3) & 'h1fffffff;
      "ir" : val = (val >> 2) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "medeleg") begin
    case(field)
      "deleg" : val = val & 'hffffffff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mideleg") begin
    case(field)
      "meip" : val = (val >> 11) & 'h1;
      "msip" : val = (val >> 3) & 'h1;
      "mtip" : val = (val >> 7) & 'h1;
      "seip" : val = (val >> 9) & 'h1;
      "sgeip" : val = (val >> 12) & 'h1;
      "ssip" : val = (val >> 1) & 'h1;
      "stip" : val = (val >> 5) & 'h1;
      "vgeip" : val = (val >> 10) & 'h1;
      "vssip" : val = (val >> 2) & 'h1;
      "vstip" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mie") begin
    case(field)
      "meie" : val = (val >> 11) & 'h1;
      "msee" : val = (val >> 3) & 'h1;
      "mtie" : val = (val >> 7) & 'h1;
      "seie" : val = (val >> 9) & 'h1;
      "sgeie" : val = (val >> 12) & 'h1;
      "ssie" : val = (val >> 1) & 'h1;
      "stie" : val = (val >> 5) & 'h1;
      "vgeie" : val = (val >> 10) & 'h1;
      "vssie" : val = (val >> 2) & 'h1;
      "vstie" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mip") begin
    case(field)
      "meip" : val = (val >> 11) & 'h1;
      "msip" : val = (val >> 3) & 'h1;
      "mtip" : val = (val >> 7) & 'h1;
      "seip" : val = (val >> 9) & 'h1;
      "sgeip" : val = (val >> 12) & 'h1;
      "ssip" : val = (val >> 1) & 'h1;
      "stip" : val = (val >> 5) & 'h1;
      "vgeip" : val = (val >> 10) & 'h1;
      "vssip" : val = (val >> 2) & 'h1;
      "vstip" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "misa") begin
    case(field)
      "exts" : val = val & 'h3ffffff;
`ifdef XLEN32
      "mxl" : val = (val >> 30) & 32'h3;
`endif
`ifdef XLEN64
      "mxl" : val = (val >> 62) & 64'h3;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mseccfg") begin
    case(field)
      "mml" : val = val & 'h1;
      "mmwp" : val = (val >> 1) & 'h1;
      "rlb" : val = (val >> 2) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mstatus") begin
    case(field)
      "fs" : val = (val >> 13) & 'h3;
`ifdef XLEN64
      "gva" : val = (val >> 38) & 64'h1;
`endif
`ifdef XLEN64
      "mbe" : val = (val >> 37) & 64'h1;
`endif
      "mie" : val = (val >> 3) & 'h1;
      "mpie" : val = (val >> 7) & 'h1;
      "mpp" : val = (val >> 11) & 'h3;
      "mprv" : val = (val >> 17) & 'h1;
`ifdef XLEN64
      "mpv" : val = (val >> 39) & 64'h1;
`endif
      "mxr" : val = (val >> 19) & 'h1;
`ifdef XLEN64
      "sbe" : val = (val >> 36) & 64'h1;
`endif
`ifdef XLEN32
      "sd" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN64
      "sd" : val = (val >> 63) & 64'h1;
`endif
      "sie" : val = (val >> 1) & 'h1;
      "spie" : val = (val >> 5) & 'h1;
      "spp" : val = (val >> 8) & 'h1;
      "sum" : val = (val >> 18) & 'h1;
`ifdef XLEN64
      "sxl" : val = (val >> 34) & 64'h3;
`endif
      "tsr" : val = (val >> 22) & 'h1;
      "tvm" : val = (val >> 20) & 'h1;
      "tw" : val = (val >> 21) & 'h1;
      "ube" : val = (val >> 6) & 'h1;
`ifdef XLEN64
      "uxl" : val = (val >> 32) & 64'h3;
`endif
      "vs" : val = (val >> 9) & 'h3;
      "xs" : val = (val >> 15) & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mstatush") begin
    case(field)
`ifdef XLEN32
      "gva" : val = (val >> 6) & 32'h1;
`endif
`ifdef XLEN32
      "mbe" : val = (val >> 5) & 32'h1;
`endif
`ifdef XLEN32
      "mpv" : val = (val >> 7) & 32'h1;
`endif
`ifdef XLEN32
      "sbe" : val = (val >> 4) & 32'h1;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "mtvec") begin
    case(field)
      "mode" : val = val & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "pmpcfg0") begin
    case(field)
      "pmp0cfg_a" : val = (val >> 3) & 'h3;
      "pmp0cfg_l" : val = (val >> 7) & 'h1;
      "pmp0cfg_xwr" : val = val & 'h7;
      "pmp1cfg_a" : val = (val >> 11) & 'h3;
      "pmp1cfg_l" : val = (val >> 15) & 'h1;
      "pmp1cfg_xwr" : val = (val >> 8) & 'h7;
      "pmp2cfg_a" : val = (val >> 19) & 'h3;
      "pmp2cfg_l" : val = (val >> 23) & 'h1;
      "pmp2cfg_xwr" : val = (val >> 16) & 'h7;
      "pmp3cfg_a" : val = (val >> 27) & 'h3;
      "pmp3cfg_l" : val = (val >> 31) & 'h1;
      "pmp3cfg_xwr" : val = (val >> 24) & 'h7;
`ifdef XLEN64
      "pmp4cfg_a" : val = (val >> 35) & 64'h3;
`endif
`ifdef XLEN64
      "pmp4cfg_l" : val = (val >> 39) & 64'h1;
`endif
`ifdef XLEN64
      "pmp4cfg_xwr" : val = (val >> 32) & 64'h7;
`endif
`ifdef XLEN64
      "pmp5cfg_a" : val = (val >> 43) & 64'h3;
`endif
`ifdef XLEN64
      "pmp5cfg_l" : val = (val >> 47) & 64'h1;
`endif
`ifdef XLEN64
      "pmp5cfg_xwr" : val = (val >> 40) & 64'h7;
`endif
`ifdef XLEN64
      "pmp6cfg_a" : val = (val >> 51) & 64'h3;
`endif
`ifdef XLEN64
      "pmp6cfg_l" : val = (val >> 55) & 64'h1;
`endif
`ifdef XLEN64
      "pmp6cfg_xwr" : val = (val >> 48) & 64'h7;
`endif
`ifdef XLEN64
      "pmp7cfg_a" : val = (val >> 59) & 64'h3;
`endif
`ifdef XLEN64
      "pmp7cfg_l" : val = (val >> 63) & 64'h1;
`endif
`ifdef XLEN64
      "pmp7cfg_xwr" : val = (val >> 56) & 64'h7;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "pmpcfg1") begin
    case(field)
`ifdef XLEN32
      "pmp4cfg_a" : val = (val >> 3) & 32'h3;
`endif
`ifdef XLEN32
      "pmp4cfg_l" : val = (val >> 7) & 32'h1;
`endif
`ifdef XLEN32
      "pmp4cfg_xwr" : val = val & 32'h7;
`endif
`ifdef XLEN32
      "pmp5cfg_a" : val = (val >> 11) & 32'h3;
`endif
`ifdef XLEN32
      "pmp5cfg_l" : val = (val >> 15) & 32'h1;
`endif
`ifdef XLEN32
      "pmp5cfg_xwr" : val = (val >> 8) & 32'h7;
`endif
`ifdef XLEN32
      "pmp6cfg_a" : val = (val >> 19) & 32'h3;
`endif
`ifdef XLEN32
      "pmp6cfg_l" : val = (val >> 23) & 32'h1;
`endif
`ifdef XLEN32
      "pmp6cfg_xwr" : val = (val >> 16) & 32'h7;
`endif
`ifdef XLEN32
      "pmp7cfg_a" : val = (val >> 27) & 32'h3;
`endif
`ifdef XLEN32
      "pmp7cfg_l" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN32
      "pmp7cfg_xwr" : val = (val >> 24) & 32'h7;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "pmpcfg2") begin
    case(field)
      "pmp10cfg_a" : val = (val >> 19) & 'h3;
      "pmp10cfg_l" : val = (val >> 23) & 'h1;
      "pmp10cfg_xwr" : val = (val >> 16) & 'h7;
      "pmp11cfg_a" : val = (val >> 27) & 'h3;
      "pmp11cfg_l" : val = (val >> 31) & 'h1;
      "pmp11cfg_xwr" : val = (val >> 24) & 'h7;
`ifdef XLEN64
      "pmp12cfg_a" : val = (val >> 35) & 64'h3;
`endif
`ifdef XLEN64
      "pmp12cfg_l" : val = (val >> 39) & 64'h1;
`endif
`ifdef XLEN64
      "pmp12cfg_xwr" : val = (val >> 32) & 64'h7;
`endif
`ifdef XLEN64
      "pmp13cfg_a" : val = (val >> 43) & 64'h3;
`endif
`ifdef XLEN64
      "pmp13cfg_l" : val = (val >> 47) & 64'h1;
`endif
`ifdef XLEN64
      "pmp13cfg_xwr" : val = (val >> 40) & 64'h7;
`endif
`ifdef XLEN64
      "pmp14cfg_a" : val = (val >> 51) & 64'h3;
`endif
`ifdef XLEN64
      "pmp14cfg_l" : val = (val >> 55) & 64'h1;
`endif
`ifdef XLEN64
      "pmp14cfg_xwr" : val = (val >> 48) & 64'h7;
`endif
`ifdef XLEN64
      "pmp15cfg_a" : val = (val >> 59) & 64'h3;
`endif
`ifdef XLEN64
      "pmp15cfg_l" : val = (val >> 63) & 64'h1;
`endif
`ifdef XLEN64
      "pmp15cfg_xwr" : val = (val >> 56) & 64'h7;
`endif
      "pmp8cfg_a" : val = (val >> 3) & 'h3;
      "pmp8cfg_l" : val = (val >> 7) & 'h1;
      "pmp8cfg_xwr" : val = val & 'h7;
      "pmp9cfg_a" : val = (val >> 11) & 'h3;
      "pmp9cfg_l" : val = (val >> 15) & 'h1;
      "pmp9cfg_xwr" : val = (val >> 8) & 'h7;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "pmpcfg3") begin
    case(field)
`ifdef XLEN32
      "pmp12cfg_a" : val = (val >> 3) & 32'h3;
`endif
`ifdef XLEN32
      "pmp12cfg_l" : val = (val >> 7) & 32'h1;
`endif
`ifdef XLEN32
      "pmp12cfg_xwr" : val = val & 32'h7;
`endif
`ifdef XLEN32
      "pmp13cfg_a" : val = (val >> 11) & 32'h3;
`endif
`ifdef XLEN32
      "pmp13cfg_l" : val = (val >> 15) & 32'h1;
`endif
`ifdef XLEN32
      "pmp13cfg_xwr" : val = (val >> 8) & 32'h7;
`endif
`ifdef XLEN32
      "pmp14cfg_a" : val = (val >> 19) & 32'h3;
`endif
`ifdef XLEN32
      "pmp14cfg_l" : val = (val >> 23) & 32'h1;
`endif
`ifdef XLEN32
      "pmp14cfg_xwr" : val = (val >> 16) & 32'h7;
`endif
`ifdef XLEN32
      "pmp15cfg_a" : val = (val >> 27) & 32'h3;
`endif
`ifdef XLEN32
      "pmp15cfg_l" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN32
      "pmp15cfg_xwr" : val = (val >> 24) & 32'h7;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "satp") begin
    case(field)
`ifdef XLEN32
      "mode" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN64
      "mode" : val = (val >> 60) & 64'hf;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "scause") begin
    case(field)
`ifdef XLEN32
      "int" : val = val & 32'hffffffff;
`endif
`ifdef XLEN64
      "int" : val = val & 64'hffffffffffffffff;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "scounteren") begin
    case(field)
      "cy" : val = val & 'h1;
      "enable" : val = (val >> 3) & 'h1fffffff;
      "ir" : val = (val >> 2) & 'h1;
      "tm" : val = (val >> 1) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "seed") begin
    case(field)
`ifdef XLEN32
      "OPST" : val = (val >> 30) & 32'h3;
`endif
`ifdef XLEN64
      "entropy" : val = val & 32'hffff;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "sie") begin
    case(field)
      "seie" : val = (val >> 9) & 'h1;
      "ssie" : val = (val >> 1) & 'h1;
      "stie" : val = (val >> 5) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "sip") begin
    case(field)
      "seip" : val = (val >> 9) & 'h1;
      "ssip" : val = (val >> 1) & 'h1;
      "stip" : val = (val >> 5) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "sstatus") begin
    case(field)
      "fs" : val = (val >> 13) & 'h3;
      "mxr" : val = (val >> 19) & 'h1;
`ifdef XLEN32
      "sd" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN64
      "sd" : val = (val >> 63) & 64'h1;
`endif
      "sie" : val = (val >> 1) & 'h1;
      "spie" : val = (val >> 5) & 'h1;
      "spp" : val = (val >> 8) & 'h1;
      "sum" : val = (val >> 18) & 'h1;
      "ube" : val = (val >> 6) & 'h1;
`ifdef XLEN64
      "uxl" : val = (val >> 32) & 64'h3;
`endif
      "vs" : val = (val >> 23) & 'h3;
      "xs" : val = (val >> 15) & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "stvec") begin
    case(field)
      "mode" : val = val & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "tcontrol") begin
    case(field)
      "mpte" : val = (val >> 7) & 'h1;
      "mte" : val = (val >> 3) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "tdata1") begin
    case(field)
`ifdef XLEN32
      "dmode" : val = (val >> 27) & 32'h1;
`endif
`ifdef XLEN64
      "dmode" : val = (val >> 59) & 64'h1;
`endif
`ifdef XLEN32
      "type" : val = (val >> 28) & 32'hf;
`endif
`ifdef XLEN64
      "type" : val = (val >> 60) & 64'hf;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "textra32") begin
    case(field)
`ifdef XLEN32
      "mselect" : val = (val >> 25) & 32'h1;
`endif
`ifdef XLEN32
      "sselect" : val = val & 32'h3;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "textra64") begin
    case(field)
`ifdef XLEN64
      "mselect" : val = (val >> 50) & 64'h1;
`endif
`ifdef XLEN64
      "sselect" : val = val & 64'h3;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "tinfo") begin
    case(field)
      "info" : val = val & 'hffff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vcsr") begin
    case(field)
      "vxsat" : val = val & 'h1;
      "vxrm"  : val = (val >> 1) & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vl") begin
    case(field)
      "vl" : val = val & 'hffff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vlenb") begin
    case(field)
      "vlenb" : val = val & 'h1fff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vsatp") begin
    case(field)
`ifdef XLEN32
      "mode" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN64
      "mode" : val = (val >> 60) & 64'hf;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vscause") begin
    case(field)
`ifdef XLEN32
      "int" : val = val & 32'hffffffff;
`endif
`ifdef XLEN64
      "int" : val = val & 64'hffffffffffffffff;
`endif
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vsie") begin
    case(field)
      "seie" : val = (val >> 9) & 'h1;
      "ssie" : val = (val >> 1) & 'h1;
      "stie" : val = (val >> 5) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vsip") begin
    case(field)
      "seip" : val = (val >> 9) & 'h1;
      "ssip" : val = (val >> 1) & 'h1;
      "stip" : val = (val >> 5) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vsstatus") begin
    case(field)
      "fs" : val = (val >> 13) & 'h3;
      "mxr" : val = (val >> 19) & 'h1;
`ifdef XLEN32
      "sd" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN64
      "sd" : val = (val >> 63) & 64'h1;
`endif
      "sie" : val = (val >> 1) & 'h1;
      "spie" : val = (val >> 5) & 'h1;
      "spp" : val = (val >> 8) & 'h1;
      "sum" : val = (val >> 18) & 'h1;
      "ube" : val = (val >> 6) & 'h1;
`ifdef XLEN64
      "uxl" : val = (val >> 32) & 64'h3;
`endif
      "vs" : val = (val >> 9) & 'h3;
      "xs" : val = (val >> 15) & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vstart") begin
    case(field)
      "vstart" : val = val & 'hffff;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vstvec") begin
    case(field)
      "mode" : val = val & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vtype") begin
    case(field)
`ifdef XLEN32
      "vill" : val = (val >> 31) & 32'h1;
`endif
`ifdef XLEN64
      "vill" : val = (val >> 63) & 64'h1;
`endif
      "vlmul" : val = val & 'h7;
      "vma" : val = (val >> 7) & 'h1;
      "vsew" : val = (val >> 3) & 'h7;
      "vta" : val = (val >> 6) & 'h1;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vxrm") begin
    case(field)
      "vxrm" : val = val & 'h3;
      default: val = 0; // Todo: error
    endcase
  end
  if (name == "vxsat") begin
    case(field)
      "vxsat" : val = val & 'h1;
      default: val = 0; // Todo: error
    endcase
  if (name == "mstateen0") begin
    case(field)
      "fcsr"    : val = (val >> 1)  & 'h1;
      "jvt"     : val = (val >> 2)  & 'h1;
      "ctr"     : val = (val >> 54) & 'h1;
      "srmcfg"  : val = (val >> 55) & 'h1;
      "p1p13"   : val = (val >> 56) & 'h1;
      "context" : val = (val >> 57) & 'h1;
      "imsic"   : val = (val >> 58) & 'h1;
      "aia"     : val = (val >> 59) & 'h1;
      "csrind"  : val = (val >> 60) & 'h1;
      "envcfg"  : val = (val >> 62) & 'h1;
      "se0"     : val = (val >> 63) & 'h1;
      default: val = 0;
    endcase
  end
  return val;
endfunction
