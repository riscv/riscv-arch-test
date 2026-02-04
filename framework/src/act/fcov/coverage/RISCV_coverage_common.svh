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

// Print coverage information if not in quiet mode
`ifndef COVER_QUIET
  `define cover_info(s)     $display(s);
`else
  `define cover_info(s)
`endif

// Constants
`define SAMPLE_AFTER 0
`define SAMPLE_BEFORE 1
`define SAMPLE_CURRENT 0
`define SAMPLE_PREV 1
`define NUM_RVVI_DATA 5

// -----------------------------------------------------------------------------
// Physical Memory Protection (PMP) Specific Macros
// -----------------------------------------------------------------------------

`define SAFE_REGION_START   (`RAM_BASE_ADDR + `LARGEST_PROGRAM)
`define REGIONSTART        `SAFE_REGION_START

// Calculate region size g in bytes.
`define g_tor       (2 ** (`G + 2))
`define g_napot     ((`G > 1) ? (2 ** (`G + 2)) : (2 ** (`G + 3)))

// Calculate k = G - 1 trailing ones in NAPOT encoding.
`define k  ((`G > 1) ? (`G - 1) : 0)

// Address encodings

// TOR or NA4 region: directly right-shifted
`define NON_STANDARD_REGION  (`REGIONSTART >> 2)              // TOR/NA4 format: yyyyy...

// NAPOT region: add trailing 1s per `k` to form mask
`define STANDARD_REGION      ((`REGIONSTART >> 2) | ((2 ** `k) - 1)) // NAPOT format: yyyyy...0111

// XLEN64 -> [53:0] & XLEN32 -> [31:0]
`define EFFECTIVE_PMPADDR (`ifdef XLEN64 53 `else 31 `endif)
`define READ_ZERO_MASK   ~((1<<`G)-1)


// -----------------------------------------------------------------------------
//                         XLEN FLEN VLEN Macros
// -----------------------------------------------------------------------------

// XLEN/FLEN as usable numbers
`ifdef XLEN32
  `define XLEN 32
`else
  `define XLEN 64
`endif
`ifdef Q_COVERAGE
  `define FLEN 128
`elsif D_COVERAGE
  `define FLEN 64
`else
  `define FLEN 32
`endif

///////////////////////////////////////////////////
// VECTOR-RELATED MACROS
// TODO: refactor to be generated based on config
///////////////////////////////////////////////////

// VLEN as usable numbers, ifdef contents should be defined in config
`ifdef VLEN65536
  `define VLEN 65536
`elsif VLEN32768
  `define VLEN 32768
`elsif VLEN16384
  `define VLEN 16384
`elsif VLEN8192
  `define VLEN 8192
`elsif VLEN4096
  `define VLEN 4096
`elsif VLEN2048
  `define VLEN 2048
`elsif VLEN1024
  `define VLEN 1024
`elsif VLEN512
  `define VLEN 512
`elsif VLEN256
  `define VLEN 256
`elsif VLEN128
  `define VLEN 128
`elsif VLEN64
  `define VLEN 64
`elsif VLEN32
  `define VLEN 32
  `ifdef VX64_COVERAGE
    // the missing `define is intentional
    `VX64_COVERAGE_NOT_SUPPORTED_WITH_VLEN32 // this is meant to throw an error letting the user know coverage is not supported in this case as it would cause negative indexing
  `endif
`elsif VLEN16
  `define VLEN 16
  `ifdef VX64_COVERAGE
    // the missing `define is intentional
    `VX64_COVERAGE_NOT_SUPPORTED_WITH_VLEN16 // this is meant to throw an error letting the user know coverage is not supported in this case
  `endif
  `ifdef VX32_COVERAGE
    `VX32_COVERAGE_NOT_SUPPORTED_WITH_VLEN16 // this is meant to throw an error letting the user know coverage is not supported in this case
  `endif
`else
  `define VLEN 8
  `ifdef VX64_COVERAGE
    // the missing `define is intentional
    `VX64_COVERAGE_NOT_SUPPORTED_WITH_VLEN8 // this is meant to throw an error letting the user know coverage is not supported in this case
  `endif
  `ifdef VX32_COVERAGE
    // the missing `define is intentional
    `VX32_COVERAGE_NOT_SUPPORTED_WITH_VLEN8 // this is meant to throw an error letting the user know coverage is not supported in this case
  `endif
  `ifdef VX16_COVERAGE
    // the missing `define is intentional
    `VX16_COVERAGE_NOT_SUPPORTED_WITH_VLEN8 // this is meant to throw an error letting the user know coverage is not supported in this case
  `endif
`endif


// supported SEWs based on what coverages are enabled
// `ifdef VX64_COVERAGE
//   `define SEW64_SUPPORTED
// `endif
// `ifdef VX32_COVERAGE
//   `define SEW32_SUPPORTED
// `endif
// `ifdef VX16_COVERAGE
//   `define SEW16_SUPPORTED
// `endif
// `ifdef VX8_COVERAGE
//   `define SEW8_SUPPORTED
// `endif

// `ifdef VLS64_COVERAGE
//   `define SEW64_SUPPORTED
// `endif
// `ifdef VLS32_COVERAGE
//   `define SEW32_SUPPORTED
// `endif
// `ifdef VLS16_COVERAGE
//   `define SEW16_SUPPORTED
// `endif
// `ifdef VLS8_COVERAGE
//   `define SEW8_SUPPORTED
// `endif

`define SEW8_SUPPORTED
`define SEW16_SUPPORTED
`define SEW32_SUPPORTED
`define SEW64_SUPPORTED

// ELEN (max SEW) definition
`ifdef VX64_COVERAGE
  `define ELEN64
`else
  `ifdef VX32_COVERAGE
    `define ELEN32
  `else
    `ifdef VX16_COVERAGE
      `define ELEN16
    `else
      `define ELEN8
    `endif
  `endif
`endif

`ifdef VLS64_COVERAGE
  `define ELEN64
`else
  `ifdef VLS32_COVERAGE
    `define ELEN32
  `else
    `ifdef VLS16_COVERAGE
      `define ELEN16
    `else
      `define ELEN8
    `endif
  `endif
`endif

// edge cases
`ifdef VLEN64
  `ifdef ELEN64
    `define ELEN_EQ_VLEN
  `endif
`endif
`ifdef VLEN32
  `ifdef ELEN32
    `define ELEN_EQ_VLEN
  `endif
`endif
`ifdef VLEN16
  `ifdef ELEN16
    `define ELEN_EQ_VLEN
  `endif
`endif
`ifdef VLEN8
  `ifdef ELEN8
    `define ELEN_EQ_VLEN
  `endif
`endif

// Minimum supported LMUL
// `ifdef SEW8_SUPPORTED
//   `ifdef ELEN64
//     `define LMULf8_SUPPORTED
//     `define LMULf4_SUPPORTED
//     `define LMULf2_SUPPORTED
//   `elsif ELEN32
//     `define LMULf4_SUPPORTED
//     `define LMULf2_SUPPORTED
//   `elsif ELEN16
//     `define LMULf2_SUPPORTED
//   `endif
// `elsif SEW16_SUPPORTED
//   `ifdef ELEN64
//     `define LMULf4_SUPPORTED
//     `define LMULf2_SUPPORTED
//   `elsif ELEN32
//     `define LMULf2_SUPPORTED
//   `endif
// `elsif SEW32_SUPPORTED
//   `ifdef ELEN64
//     `define LMULf2_SUPPORTED
//   `endif
// `endif


// Set register type length
`define XLEN_BITS         bit        [`XLEN-1:0]
`define SIGNED_XLEN_BITS  bit signed [`XLEN-1:0]
`define FLEN_BITS         bit        [`FLEN-1:0]
`define SIGNED_FLEN_BITS  bit signed [`FLEN-1:0]
`define VLEN_BITS         bit        [`VLEN-1:0]
`define SIGNED_VLEN_BITS  bit signed [`VLEN-1:0]

// Instruction operand data structure
typedef struct {
  string key;
  string val;
} ops_t;

// Register data structures for GPRs and FPRs
typedef enum {
  x0,
  x1,
  x2,
  x3,
  x4,
  x5,
  x6,
  x7,
  x8,
  x9,
  x10,
  x11,
  x12,
  x13,
  x14,
  x15
`ifndef COVER_E
  ,
  x16,
  x17,
  x18,
  x19,
  x20,
  x21,
  x22,
  x23,
  x24,
  x25,
  x26,
  x27,
  x28,
  x29,
  x30,
  x31
`endif
} gpr_name_t;

typedef enum {
  c_x8,
  c_x9,
  c_x10,
  c_x11,
  c_x12,
  c_x13,
  c_x14,
  c_x15
} gpr_reduced_name_t;

typedef enum {
  f0,
  f1,
  f2,
  f3,
  f4,
  f5,
  f6,
  f7,
  f8,
  f9,
  f10,
  f11,
  f12,
  f13,
  f14,
  f15,
  f16,
  f17,
  f18,
  f19,
  f20,
  f21,
  f22,
  f23,
  f24,
  f25,
  f26,
  f27,
  f28,
  f29,
  f30,
  f31
} fpr_name_t;

typedef enum {
  v0,
  v1,
  v2,
  v3,
  v4,
  v5,
  v6,
  v7,
  v8,
  v9,
  v10,
  v11,
  v12,
  v13,
  v14,
  v15,
  v16,
  v17,
  v18,
  v19,
  v20,
  v21,
  v22,
  v23,
  v24,
  v25,
  v26,
  v27,
  v28,
  v29,
  v30,
  v31
} vr_name_t;

typedef enum {
  c_f8,
  c_f9,
  c_f10,
  c_f11,
  c_f12,
  c_f13,
  c_f14,
  c_f15
} fpr_reduced_name_t;


// Register name conversion functions
function int get_gpr_num(string key);
  case(key)
    "x0": return 0;
    "zero": return 0;
    "x1": return 1;
    "ra": return 1;
    "x2": return 2;
    "sp": return 2;
    "x3": return 3;
    "gp": return 3;
    "x4": return 4;
    "tp": return 4;
    "x5": return 5;
    "t0": return 5;
    "x6": return 6;
    "t1": return 6;
    "x7": return 7;
    "t2": return 7;
    "x8": return 8;
    "s0": return 8;
    "x9": return 9;
    "s1": return 9;
    "x10": return 10;
    "a0": return 10;
    "x11": return 11;
    "a1": return 11;
    "x12": return 12;
    "a2": return 12;
    "x13": return 13;
    "a3": return 13;
    "x14": return 14;
    "a4": return 14;
    "x15": return 15;
    "a5": return 15;
    "x16": return 16;
    "a6": return 16;
    "x17": return 17;
    "a7": return 17;
    "x18": return 18;
    "s2": return 18;
    "x19": return 19;
    "s3": return 19;
    "x20": return 20;
    "s4": return 20;
    "x21": return 21;
    "s5": return 21;
    "x22": return 22;
    "s6": return 22;
    "x23": return 23;
    "s7": return 23;
    "x24": return 24;
    "s8": return 24;
    "x25": return 25;
    "s9": return 25;
    "x26": return 26;
    "s10": return 26;
    "x27": return 27;
    "s11": return 27;
    "x28": return 28;
    "t3": return 28;
    "x29": return 29;
    "t4": return 29;
    "x30": return 30;
    "t5": return 30;
    "x31": return 31;
    "t6": return 31;
  endcase
  return -1;
endfunction

function int get_fpr_num(string key);
  case(key)
    "f0": return 0;
    "f1": return 1;
    "f2": return 2;
    "f3": return 3;
    "f4": return 4;
    "f5": return 5;
    "f6": return 6;
    "f7": return 7;
    "f8": return 8;
    "f9": return 9;
    "f10": return 10;
    "f11": return 11;
    "f12": return 12;
    "f13": return 13;
    "f14": return 14;
    "f15": return 15;
    "f16": return 16;
    "f17": return 17;
    "f18": return 18;
    "f19": return 19;
    "f20": return 20;
    "f21": return 21;
    "f22": return 22;
    "f23": return 23;
    "f24": return 24;
    "f25": return 25;
    "f26": return 26;
    "f27": return 27;
    "f28": return 28;
    "f29": return 29;
    "f30": return 30;
    "f31": return 31;
  endcase
  return -1;
endfunction

function int get_vr_num(string key);
  case(key)
    "v0": return 0;
    "v1": return 1;
    "v2": return 2;
    "v3": return 3;
    "v4": return 4;
    "v5": return 5;
    "v6": return 6;
    "v7": return 7;
    "v8": return 8;
    "v9": return 9;
    "v10": return 10;
    "v11": return 11;
    "v12": return 12;
    "v13": return 13;
    "v14": return 14;
    "v15": return 15;
    "v16": return 16;
    "v17": return 17;
    "v18": return 18;
    "v19": return 19;
    "v20": return 20;
    "v21": return 21;
    "v22": return 22;
    "v23": return 23;
    "v24": return 24;
    "v25": return 25;
    "v26": return 26;
    "v27": return 27;
    "v28": return 28;
    "v29": return 29;
    "v30": return 30;
    "v31": return 31;
  endcase
  return -1;
endfunction


// Floating point rounding modes
typedef enum {
  dyn,
  rdn,
  rmm,
  rne,
  rtz,
  rup
} frm_name_t;

function frm_name_t get_frm(string s);
  case (s)
    "rdn": return rdn;
    "rmm": return rmm;
    "rne": return rne;
    "rtz": return rtz;
    "rup": return rup;
    default: return dyn;
  endcase
endfunction

function bit get_vm(string s);
  case (s)
    "v0.t" : return 1'b0;
    "v0"   : return 1'b0;
    ""     : return 1'b1;
    default: begin
      $error("ERROR: SystemVerilog Functional Coverage: Masking string %s is not recognized", s);
      $fatal(1);
    end
  endcase
endfunction

//Vector vsetvli parameters
// Flipped: string -> int (bits), using case statements

function bit [2:0] get_vtype_eSEW_val(string str);
  case (str)
    "e8":   return 3'b000;
    "e16":  return 3'b001;
    "e32":  return 3'b010;
    "e64":  return 3'b011;
  endcase
endfunction

function bit [2:0] get_vtype_mLMUL_val(string str);
  case (str)
    "mf8": return 3'b101;
    "mf4": return 3'b110;
    "mf2": return 3'b111;
    "m1":  return 3'b000;
    "m2":  return 3'b001;
    "m4":  return 3'b010;
    "m8":  return 3'b011;
  endcase
endfunction

function bit get_vtype_ta_val(string str);
  case (str)
    "ta": return 1'b1;
    "tu": return 1'b0;
  endcase
endfunction

function bit get_vtype_ma_val(string str);
  case (str)
    "ma": return 1'b1;
    "mu": return 1'b0;
  endcase
endfunction


// CSR address conversion
function int get_csr_addr(int hart, string s);
  import RISCV_decode_pkg::*;
  case(s)
    "fflags": return CSR_FFLAGS;
    "frm": return CSR_FRM;
    "fcsr": return CSR_FCSR;
    "vstart": return CSR_VSTART;
    "vxsat": return CSR_VXSAT;
    "vxrm": return CSR_VXRM;
    "vcsr": return CSR_VCSR;
    "ssp": return CSR_SSP;
    "seed": return CSR_SEED;
    "jvt": return CSR_JVT;
    "cycle": return CSR_CYCLE;
    "time": return CSR_TIME;
    "instret": return CSR_INSTRET;
    "hpmcounter3": return CSR_HPMCOUNTER3;
    "hpmcounter4": return CSR_HPMCOUNTER4;
    "hpmcounter5": return CSR_HPMCOUNTER5;
    "hpmcounter6": return CSR_HPMCOUNTER6;
    "hpmcounter7": return CSR_HPMCOUNTER7;
    "hpmcounter8": return CSR_HPMCOUNTER8;
    "hpmcounter9": return CSR_HPMCOUNTER9;
    "hpmcounter10": return CSR_HPMCOUNTER10;
    "hpmcounter11": return CSR_HPMCOUNTER11;
    "hpmcounter12": return CSR_HPMCOUNTER12;
    "hpmcounter13": return CSR_HPMCOUNTER13;
    "hpmcounter14": return CSR_HPMCOUNTER14;
    "hpmcounter15": return CSR_HPMCOUNTER15;
    "hpmcounter16": return CSR_HPMCOUNTER16;
    "hpmcounter17": return CSR_HPMCOUNTER17;
    "hpmcounter18": return CSR_HPMCOUNTER18;
    "hpmcounter19": return CSR_HPMCOUNTER19;
    "hpmcounter20": return CSR_HPMCOUNTER20;
    "hpmcounter21": return CSR_HPMCOUNTER21;
    "hpmcounter22": return CSR_HPMCOUNTER22;
    "hpmcounter23": return CSR_HPMCOUNTER23;
    "hpmcounter24": return CSR_HPMCOUNTER24;
    "hpmcounter25": return CSR_HPMCOUNTER25;
    "hpmcounter26": return CSR_HPMCOUNTER26;
    "hpmcounter27": return CSR_HPMCOUNTER27;
    "hpmcounter28": return CSR_HPMCOUNTER28;
    "hpmcounter29": return CSR_HPMCOUNTER29;
    "hpmcounter30": return CSR_HPMCOUNTER30;
    "hpmcounter31": return CSR_HPMCOUNTER31;
    "vl": return CSR_VL;
    "vtype": return CSR_VTYPE;
    "vlenb": return CSR_VLENB;
    "sstatus": return CSR_SSTATUS;
    "sedeleg": return CSR_SEDELEG;
    "sideleg": return CSR_SIDELEG;
    "sie": return CSR_SIE;
    "stvec": return CSR_STVEC;
    "scounteren": return CSR_SCOUNTEREN;
    "senvcfg": return CSR_SENVCFG;
    "sstateen0": return CSR_SSTATEEN0;
    "sstateen1": return CSR_SSTATEEN1;
    "sstateen2": return CSR_SSTATEEN2;
    "sstateen3": return CSR_SSTATEEN3;
    "scountinhibit": return CSR_SCOUNTINHIBIT;
    "sscratch": return CSR_SSCRATCH;
    "sepc": return CSR_SEPC;
    "scause": return CSR_SCAUSE;
    "stval": return CSR_STVAL;
    "sip": return CSR_SIP;
    "stimecmp": return CSR_STIMECMP;
    "sctrctl": return CSR_SCTRCTL;
    "sctrstatus": return CSR_SCTRSTATUS;
    "siselect": return CSR_SISELECT;
    "sireg": return CSR_SIREG;
    "sireg2": return CSR_SIREG2;
    "sireg3": return CSR_SIREG3;
    "sireg4": return CSR_SIREG4;
    "sireg5": return CSR_SIREG5;
    "sireg6": return CSR_SIREG6;
    "stopei": return CSR_STOPEI;
    "sctrdepth": return CSR_SCTRDEPTH;
    "satp": return CSR_SATP;
    "srmcfg": return CSR_SRMCFG;
    "scontext": return CSR_SCONTEXT;
    "vsstatus": return CSR_VSSTATUS;
    "vsie": return CSR_VSIE;
    "vstvec": return CSR_VSTVEC;
    "vsscratch": return CSR_VSSCRATCH;
    "vsepc": return CSR_VSEPC;
    "vscause": return CSR_VSCAUSE;
    "vstval": return CSR_VSTVAL;
    "vsip": return CSR_VSIP;
    "vstimecmp": return CSR_VSTIMECMP;
    "vsctrctl": return CSR_VSCTRCTL;
    "vsiselect": return CSR_VSISELECT;
    "vsireg": return CSR_VSIREG;
    "vsireg2": return CSR_VSIREG2;
    "vsireg3": return CSR_VSIREG3;
    "vsireg4": return CSR_VSIREG4;
    "vsireg5": return CSR_VSIREG5;
    "vsireg6": return CSR_VSIREG6;
    "vstopei": return CSR_VSTOPEI;
    "vsatp": return CSR_VSATP;
    "hstatus": return CSR_HSTATUS;
    "hedeleg": return CSR_HEDELEG;
    "hideleg": return CSR_HIDELEG;
    "hie": return CSR_HIE;
    "htimedelta": return CSR_HTIMEDELTA;
    "hcounteren": return CSR_HCOUNTEREN;
    "hgeie": return CSR_HGEIE;
    "hvien": return CSR_HVIEN;
    "hvictl": return CSR_HVICTL;
    "henvcfg": return CSR_HENVCFG;
    "hstateen0": return CSR_HSTATEEN0;
    "hstateen1": return CSR_HSTATEEN1;
    "hstateen2": return CSR_HSTATEEN2;
    "hstateen3": return CSR_HSTATEEN3;
    "htval": return CSR_HTVAL;
    "hip": return CSR_HIP;
    "hvip": return CSR_HVIP;
    "hviprio1": return CSR_HVIPRIO1;
    "hviprio2": return CSR_HVIPRIO2;
    "htinst": return CSR_HTINST;
    "hgatp": return CSR_HGATP;
    "hcontext": return CSR_HCONTEXT;
    "hgeip": return CSR_HGEIP;
    "vstopi": return CSR_VSTOPI;
    "scountovf": return CSR_SCOUNTOVF;
    "stopi": return CSR_STOPI;
    "utvt": return CSR_UTVT;
    "unxti": return CSR_UNXTI;
    "uintstatus": return CSR_UINTSTATUS;
    "uscratchcsw": return CSR_USCRATCHCSW;
    "uscratchcswl": return CSR_USCRATCHCSWL;
    "stvt": return CSR_STVT;
    "snxti": return CSR_SNXTI;
    "sintstatus": return CSR_SINTSTATUS;
    "sscratchcsw": return CSR_SSCRATCHCSW;
    "sscratchcswl": return CSR_SSCRATCHCSWL;
    "mtvt": return CSR_MTVT;
    "mnxti": return CSR_MNXTI;
    "mintstatus": return CSR_MINTSTATUS;
    "mscratchcsw": return CSR_MSCRATCHCSW;
    "mscratchcswl": return CSR_MSCRATCHCSWL;
    "mstatus": return CSR_MSTATUS;
    "misa": return CSR_MISA;
    "medeleg": return CSR_MEDELEG;
    "mideleg": return CSR_MIDELEG;
    "mie": return CSR_MIE;
    "mtvec": return CSR_MTVEC;
    "mcounteren": return CSR_MCOUNTEREN;
    "mvien": return CSR_MVIEN;
    "mvip": return CSR_MVIP;
    "menvcfg": return CSR_MENVCFG;
    "mstateen0": return CSR_MSTATEEN0;
    "mstateen1": return CSR_MSTATEEN1;
    "mstateen2": return CSR_MSTATEEN2;
    "mstateen3": return CSR_MSTATEEN3;
    "mcountinhibit": return CSR_MCOUNTINHIBIT;
    "mscratch": return CSR_MSCRATCH;
    "mepc": return CSR_MEPC;
    "mcause": return CSR_MCAUSE;
    "mtval": return CSR_MTVAL;
    "mip": return CSR_MIP;
    "mtinst": return CSR_MTINST;
    "mtval2": return CSR_MTVAL2;
    "mctrctl": return CSR_MCTRCTL;
    "miselect": return CSR_MISELECT;
    "mireg": return CSR_MIREG;
    "mireg2": return CSR_MIREG2;
    "mireg3": return CSR_MIREG3;
    "mireg4": return CSR_MIREG4;
    "mireg5": return CSR_MIREG5;
    "mireg6": return CSR_MIREG6;
    "mtopei": return CSR_MTOPEI;
    "pmpcfg0": return CSR_PMPCFG0;
    "pmpcfg1": return CSR_PMPCFG1;
    "pmpcfg2": return CSR_PMPCFG2;
    "pmpcfg3": return CSR_PMPCFG3;
    "pmpcfg4": return CSR_PMPCFG4;
    "pmpcfg5": return CSR_PMPCFG5;
    "pmpcfg6": return CSR_PMPCFG6;
    "pmpcfg7": return CSR_PMPCFG7;
    "pmpcfg8": return CSR_PMPCFG8;
    "pmpcfg9": return CSR_PMPCFG9;
    "pmpcfg10": return CSR_PMPCFG10;
    "pmpcfg11": return CSR_PMPCFG11;
    "pmpcfg12": return CSR_PMPCFG12;
    "pmpcfg13": return CSR_PMPCFG13;
    "pmpcfg14": return CSR_PMPCFG14;
    "pmpcfg15": return CSR_PMPCFG15;
    "pmpaddr0": return CSR_PMPADDR0;
    "pmpaddr1": return CSR_PMPADDR1;
    "pmpaddr2": return CSR_PMPADDR2;
    "pmpaddr3": return CSR_PMPADDR3;
    "pmpaddr4": return CSR_PMPADDR4;
    "pmpaddr5": return CSR_PMPADDR5;
    "pmpaddr6": return CSR_PMPADDR6;
    "pmpaddr7": return CSR_PMPADDR7;
    "pmpaddr8": return CSR_PMPADDR8;
    "pmpaddr9": return CSR_PMPADDR9;
    "pmpaddr10": return CSR_PMPADDR10;
    "pmpaddr11": return CSR_PMPADDR11;
    "pmpaddr12": return CSR_PMPADDR12;
    "pmpaddr13": return CSR_PMPADDR13;
    "pmpaddr14": return CSR_PMPADDR14;
    "pmpaddr15": return CSR_PMPADDR15;
    "pmpaddr16": return CSR_PMPADDR16;
    "pmpaddr17": return CSR_PMPADDR17;
    "pmpaddr18": return CSR_PMPADDR18;
    "pmpaddr19": return CSR_PMPADDR19;
    "pmpaddr20": return CSR_PMPADDR20;
    "pmpaddr21": return CSR_PMPADDR21;
    "pmpaddr22": return CSR_PMPADDR22;
    "pmpaddr23": return CSR_PMPADDR23;
    "pmpaddr24": return CSR_PMPADDR24;
    "pmpaddr25": return CSR_PMPADDR25;
    "pmpaddr26": return CSR_PMPADDR26;
    "pmpaddr27": return CSR_PMPADDR27;
    "pmpaddr28": return CSR_PMPADDR28;
    "pmpaddr29": return CSR_PMPADDR29;
    "pmpaddr30": return CSR_PMPADDR30;
    "pmpaddr31": return CSR_PMPADDR31;
    "pmpaddr32": return CSR_PMPADDR32;
    "pmpaddr33": return CSR_PMPADDR33;
    "pmpaddr34": return CSR_PMPADDR34;
    "pmpaddr35": return CSR_PMPADDR35;
    "pmpaddr36": return CSR_PMPADDR36;
    "pmpaddr37": return CSR_PMPADDR37;
    "pmpaddr38": return CSR_PMPADDR38;
    "pmpaddr39": return CSR_PMPADDR39;
    "pmpaddr40": return CSR_PMPADDR40;
    "pmpaddr41": return CSR_PMPADDR41;
    "pmpaddr42": return CSR_PMPADDR42;
    "pmpaddr43": return CSR_PMPADDR43;
    "pmpaddr44": return CSR_PMPADDR44;
    "pmpaddr45": return CSR_PMPADDR45;
    "pmpaddr46": return CSR_PMPADDR46;
    "pmpaddr47": return CSR_PMPADDR47;
    "pmpaddr48": return CSR_PMPADDR48;
    "pmpaddr49": return CSR_PMPADDR49;
    "pmpaddr50": return CSR_PMPADDR50;
    "pmpaddr51": return CSR_PMPADDR51;
    "pmpaddr52": return CSR_PMPADDR52;
    "pmpaddr53": return CSR_PMPADDR53;
    "pmpaddr54": return CSR_PMPADDR54;
    "pmpaddr55": return CSR_PMPADDR55;
    "pmpaddr56": return CSR_PMPADDR56;
    "pmpaddr57": return CSR_PMPADDR57;
    "pmpaddr58": return CSR_PMPADDR58;
    "pmpaddr59": return CSR_PMPADDR59;
    "pmpaddr60": return CSR_PMPADDR60;
    "pmpaddr61": return CSR_PMPADDR61;
    "pmpaddr62": return CSR_PMPADDR62;
    "pmpaddr63": return CSR_PMPADDR63;
    "mseccfg": return CSR_MSECCFG;
    "tselect": return CSR_TSELECT;
    "tdata1": return CSR_TDATA1;
    "tdata2": return CSR_TDATA2;
    "tdata3": return CSR_TDATA3;
    "tinfo": return CSR_TINFO;
    "tcontrol": return CSR_TCONTROL;
    "mcontext": return CSR_MCONTEXT;
    "mscontext": return CSR_MSCONTEXT;
    "dcsr": return CSR_DCSR;
    "dpc": return CSR_DPC;
    "dscratch0": return CSR_DSCRATCH0;
    "dscratch1": return CSR_DSCRATCH1;
    "mcycle": return CSR_MCYCLE;
    "minstret": return CSR_MINSTRET;
    "mhpmcounter3": return CSR_MHPMCOUNTER3;
    "mhpmcounter4": return CSR_MHPMCOUNTER4;
    "mhpmcounter5": return CSR_MHPMCOUNTER5;
    "mhpmcounter6": return CSR_MHPMCOUNTER6;
    "mhpmcounter7": return CSR_MHPMCOUNTER7;
    "mhpmcounter8": return CSR_MHPMCOUNTER8;
    "mhpmcounter9": return CSR_MHPMCOUNTER9;
    "mhpmcounter10": return CSR_MHPMCOUNTER10;
    "mhpmcounter11": return CSR_MHPMCOUNTER11;
    "mhpmcounter12": return CSR_MHPMCOUNTER12;
    "mhpmcounter13": return CSR_MHPMCOUNTER13;
    "mhpmcounter14": return CSR_MHPMCOUNTER14;
    "mhpmcounter15": return CSR_MHPMCOUNTER15;
    "mhpmcounter16": return CSR_MHPMCOUNTER16;
    "mhpmcounter17": return CSR_MHPMCOUNTER17;
    "mhpmcounter18": return CSR_MHPMCOUNTER18;
    "mhpmcounter19": return CSR_MHPMCOUNTER19;
    "mhpmcounter20": return CSR_MHPMCOUNTER20;
    "mhpmcounter21": return CSR_MHPMCOUNTER21;
    "mhpmcounter22": return CSR_MHPMCOUNTER22;
    "mhpmcounter23": return CSR_MHPMCOUNTER23;
    "mhpmcounter24": return CSR_MHPMCOUNTER24;
    "mhpmcounter25": return CSR_MHPMCOUNTER25;
    "mhpmcounter26": return CSR_MHPMCOUNTER26;
    "mhpmcounter27": return CSR_MHPMCOUNTER27;
    "mhpmcounter28": return CSR_MHPMCOUNTER28;
    "mhpmcounter29": return CSR_MHPMCOUNTER29;
    "mhpmcounter30": return CSR_MHPMCOUNTER30;
    "mhpmcounter31": return CSR_MHPMCOUNTER31;
    "mcyclecfg": return CSR_MCYCLECFG;
    "minstretcfg": return CSR_MINSTRETCFG;
    "mhpmevent3": return CSR_MHPMEVENT3;
    "mhpmevent4": return CSR_MHPMEVENT4;
    "mhpmevent5": return CSR_MHPMEVENT5;
    "mhpmevent6": return CSR_MHPMEVENT6;
    "mhpmevent7": return CSR_MHPMEVENT7;
    "mhpmevent8": return CSR_MHPMEVENT8;
    "mhpmevent9": return CSR_MHPMEVENT9;
    "mhpmevent10": return CSR_MHPMEVENT10;
    "mhpmevent11": return CSR_MHPMEVENT11;
    "mhpmevent12": return CSR_MHPMEVENT12;
    "mhpmevent13": return CSR_MHPMEVENT13;
    "mhpmevent14": return CSR_MHPMEVENT14;
    "mhpmevent15": return CSR_MHPMEVENT15;
    "mhpmevent16": return CSR_MHPMEVENT16;
    "mhpmevent17": return CSR_MHPMEVENT17;
    "mhpmevent18": return CSR_MHPMEVENT18;
    "mhpmevent19": return CSR_MHPMEVENT19;
    "mhpmevent20": return CSR_MHPMEVENT20;
    "mhpmevent21": return CSR_MHPMEVENT21;
    "mhpmevent22": return CSR_MHPMEVENT22;
    "mhpmevent23": return CSR_MHPMEVENT23;
    "mhpmevent24": return CSR_MHPMEVENT24;
    "mhpmevent25": return CSR_MHPMEVENT25;
    "mhpmevent26": return CSR_MHPMEVENT26;
    "mhpmevent27": return CSR_MHPMEVENT27;
    "mhpmevent28": return CSR_MHPMEVENT28;
    "mhpmevent29": return CSR_MHPMEVENT29;
    "mhpmevent30": return CSR_MHPMEVENT30;
    "mhpmevent31": return CSR_MHPMEVENT31;
    "mvendorid": return CSR_MVENDORID;
    "marchid": return CSR_MARCHID;
    "mimpid": return CSR_MIMPID;
    "mhartid": return CSR_MHARTID;
    "mconfigptr": return CSR_MCONFIGPTR;
    "mtopi": return CSR_MTOPI;
    "sieh": return CSR_SIEH;
    "siph": return CSR_SIPH;
    "stimecmph": return CSR_STIMECMPH;
    "vsieh": return CSR_VSIEH;
    "vsiph": return CSR_VSIPH;
    "vstimecmph": return CSR_VSTIMECMPH;
    "hedelegh": return CSR_HEDELEGH;
    "htimedeltah": return CSR_HTIMEDELTAH;
    "hidelegh": return CSR_HIDELEGH;
    "hvienh": return CSR_HVIENH;
    "henvcfgh": return CSR_HENVCFGH;
    "hviph": return CSR_HVIPH;
    "hviprio1h": return CSR_HVIPRIO1H;
    "hviprio2h": return CSR_HVIPRIO2H;
    "hstateen0h": return CSR_HSTATEEN0H;
    "hstateen1h": return CSR_HSTATEEN1H;
    "hstateen2h": return CSR_HSTATEEN2H;
    "hstateen3h": return CSR_HSTATEEN3H;
    "cycleh": return CSR_CYCLEH;
    "timeh": return CSR_TIMEH;
    "instreth": return CSR_INSTRETH;
    "hpmcounter3h": return CSR_HPMCOUNTER3H;
    "hpmcounter4h": return CSR_HPMCOUNTER4H;
    "hpmcounter5h": return CSR_HPMCOUNTER5H;
    "hpmcounter6h": return CSR_HPMCOUNTER6H;
    "hpmcounter7h": return CSR_HPMCOUNTER7H;
    "hpmcounter8h": return CSR_HPMCOUNTER8H;
    "hpmcounter9h": return CSR_HPMCOUNTER9H;
    "hpmcounter10h": return CSR_HPMCOUNTER10H;
    "hpmcounter11h": return CSR_HPMCOUNTER11H;
    "hpmcounter12h": return CSR_HPMCOUNTER12H;
    "hpmcounter13h": return CSR_HPMCOUNTER13H;
    "hpmcounter14h": return CSR_HPMCOUNTER14H;
    "hpmcounter15h": return CSR_HPMCOUNTER15H;
    "hpmcounter16h": return CSR_HPMCOUNTER16H;
    "hpmcounter17h": return CSR_HPMCOUNTER17H;
    "hpmcounter18h": return CSR_HPMCOUNTER18H;
    "hpmcounter19h": return CSR_HPMCOUNTER19H;
    "hpmcounter20h": return CSR_HPMCOUNTER20H;
    "hpmcounter21h": return CSR_HPMCOUNTER21H;
    "hpmcounter22h": return CSR_HPMCOUNTER22H;
    "hpmcounter23h": return CSR_HPMCOUNTER23H;
    "hpmcounter24h": return CSR_HPMCOUNTER24H;
    "hpmcounter25h": return CSR_HPMCOUNTER25H;
    "hpmcounter26h": return CSR_HPMCOUNTER26H;
    "hpmcounter27h": return CSR_HPMCOUNTER27H;
    "hpmcounter28h": return CSR_HPMCOUNTER28H;
    "hpmcounter29h": return CSR_HPMCOUNTER29H;
    "hpmcounter30h": return CSR_HPMCOUNTER30H;
    "hpmcounter31h": return CSR_HPMCOUNTER31H;
    "mstatush": return CSR_MSTATUSH;
    "midelegh": return CSR_MIDELEGH;
    "mieh": return CSR_MIEH;
    "mvienh": return CSR_MVIENH;
    "mviph": return CSR_MVIPH;
    "menvcfgh": return CSR_MENVCFGH;
    "mstateen0h": return CSR_MSTATEEN0H;
    "mstateen1h": return CSR_MSTATEEN1H;
    "mstateen2h": return CSR_MSTATEEN2H;
    "mstateen3h": return CSR_MSTATEEN3H;
    "miph": return CSR_MIPH;
    "mcyclecfgh": return CSR_MCYCLECFGH;
    "minstretcfgh": return CSR_MINSTRETCFGH;
    "mhpmevent3h": return CSR_MHPMEVENT3H;
    "mhpmevent4h": return CSR_MHPMEVENT4H;
    "mhpmevent5h": return CSR_MHPMEVENT5H;
    "mhpmevent6h": return CSR_MHPMEVENT6H;
    "mhpmevent7h": return CSR_MHPMEVENT7H;
    "mhpmevent8h": return CSR_MHPMEVENT8H;
    "mhpmevent9h": return CSR_MHPMEVENT9H;
    "mhpmevent10h": return CSR_MHPMEVENT10H;
    "mhpmevent11h": return CSR_MHPMEVENT11H;
    "mhpmevent12h": return CSR_MHPMEVENT12H;
    "mhpmevent13h": return CSR_MHPMEVENT13H;
    "mhpmevent14h": return CSR_MHPMEVENT14H;
    "mhpmevent15h": return CSR_MHPMEVENT15H;
    "mhpmevent16h": return CSR_MHPMEVENT16H;
    "mhpmevent17h": return CSR_MHPMEVENT17H;
    "mhpmevent18h": return CSR_MHPMEVENT18H;
    "mhpmevent19h": return CSR_MHPMEVENT19H;
    "mhpmevent20h": return CSR_MHPMEVENT20H;
    "mhpmevent21h": return CSR_MHPMEVENT21H;
    "mhpmevent22h": return CSR_MHPMEVENT22H;
    "mhpmevent23h": return CSR_MHPMEVENT23H;
    "mhpmevent24h": return CSR_MHPMEVENT24H;
    "mhpmevent25h": return CSR_MHPMEVENT25H;
    "mhpmevent26h": return CSR_MHPMEVENT26H;
    "mhpmevent27h": return CSR_MHPMEVENT27H;
    "mhpmevent28h": return CSR_MHPMEVENT28H;
    "mhpmevent29h": return CSR_MHPMEVENT29H;
    "mhpmevent30h": return CSR_MHPMEVENT30H;
    "mhpmevent31h": return CSR_MHPMEVENT31H;
    "mnscratch": return CSR_MNSCRATCH;
    "mnepc": return CSR_MNEPC;
    "mncause": return CSR_MNCAUSE;
    "mnstatus": return CSR_MNSTATUS;
    "mseccfgh": return CSR_MSECCFGH;
    "mcycleh": return CSR_MCYCLEH;
    "minstreth": return CSR_MINSTRETH;
    "mhpmcounter3h": return CSR_MHPMCOUNTER3H;
    "mhpmcounter4h": return CSR_MHPMCOUNTER4H;
    "mhpmcounter5h": return CSR_MHPMCOUNTER5H;
    "mhpmcounter6h": return CSR_MHPMCOUNTER6H;
    "mhpmcounter7h": return CSR_MHPMCOUNTER7H;
    "mhpmcounter8h": return CSR_MHPMCOUNTER8H;
    "mhpmcounter9h": return CSR_MHPMCOUNTER9H;
    "mhpmcounter10h": return CSR_MHPMCOUNTER10H;
    "mhpmcounter11h": return CSR_MHPMCOUNTER11H;
    "mhpmcounter12h": return CSR_MHPMCOUNTER12H;
    "mhpmcounter13h": return CSR_MHPMCOUNTER13H;
    "mhpmcounter14h": return CSR_MHPMCOUNTER14H;
    "mhpmcounter15h": return CSR_MHPMCOUNTER15H;
    "mhpmcounter16h": return CSR_MHPMCOUNTER16H;
    "mhpmcounter17h": return CSR_MHPMCOUNTER17H;
    "mhpmcounter18h": return CSR_MHPMCOUNTER18H;
    "mhpmcounter19h": return CSR_MHPMCOUNTER19H;
    "mhpmcounter20h": return CSR_MHPMCOUNTER20H;
    "mhpmcounter21h": return CSR_MHPMCOUNTER21H;
    "mhpmcounter22h": return CSR_MHPMCOUNTER22H;
    "mhpmcounter23h": return CSR_MHPMCOUNTER23H;
    "mhpmcounter24h": return CSR_MHPMCOUNTER24H;
    "mhpmcounter25h": return CSR_MHPMCOUNTER25H;
    "mhpmcounter26h": return CSR_MHPMCOUNTER26H;
    "mhpmcounter27h": return CSR_MHPMCOUNTER27H;
    "mhpmcounter28h": return CSR_MHPMCOUNTER28H;
    "mhpmcounter29h": return CSR_MHPMCOUNTER29H;
    "mhpmcounter30h": return CSR_MHPMCOUNTER30H;
    "mhpmcounter31h": return CSR_MHPMCOUNTER31H;
  endcase
endfunction
