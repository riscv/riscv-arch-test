///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Instruction Disassembler Helper Functions
//
// Copyright (C) 2025 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written: Jordan Carlin jcarlin@hmc.edu February 2024
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

// Integer register number to string
function string get_gpr_name(int key);
  case(key)
`ifndef ABI_REG_NAMES
    0: return "x0";
    1: return "x1";
    2: return "x2";
    3: return "x3";
    4: return "x4";
    5: return "x5";
    6: return "x6";
    7: return "x7";
    8: return "x8";
    9: return "x9";
    10: return "x10";
    11: return "x11";
    12: return "x12";
    13: return "x13";
    14: return "x14";
    15: return "x15";
    16: return "x16";
    17: return "x17";
    18: return "x18";
    19: return "x19";
    20: return "x20";
    21: return "x21";
    22: return "x22";
    23: return "x23";
    24: return "x24";
    25: return "x25";
    26: return "x26";
    27: return "x27";
    28: return "x28";
    29: return "x29";
    30: return "x30";
    31: return "x31";
`else
    0: return "zero";
    1: return "ra";
    2: return "sp";
    3: return "gp";
    4: return "tp";
    5: return "t0";
    6: return "t1";
    7: return "t2";
    8: return "s0";
    9: return "s1";
    10: return "a0";
    11: return "a1";
    12: return "a2";
    13: return "a3";
    14: return "a4";
    15: return "a5";
    16: return "a6";
    17: return "a7";
    18: return "s2";
    19: return "s3";
    20: return "s4";
    21: return "s5";
    22: return "s6";
    23: return "s7";
    24: return "s8";
    25: return "s9";
    26: return "s10";
    27: return "s11";
    28: return "t3";
    29: return "t4";
    30: return "t5";
    31: return "t6";
`endif
    default: begin
          $error("ERROR: SystemVerilog Functional Coverage: get_gpr_name(%0s) not found gpr", key);
          $fatal(1);
      end
  endcase
endfunction

// Floating point register number to string
function string get_fpr_name(int key);
  case(key)
    0: return "f0";
    1: return "f1";
    2: return "f2";
    3: return "f3";
    4: return "f4";
    5: return "f5";
    6: return "f6";
    7: return "f7";
    8: return "f8";
    9: return "f9";
    10: return "f10";
    11: return "f11";
    12: return "f12";
    13: return "f13";
    14: return "f14";
    15: return "f15";
    16: return "f16";
    17: return "f17";
    18: return "f18";
    19: return "f19";
    20: return "f20";
    21: return "f21";
    22: return "f22";
    23: return "f23";
    24: return "f24";
    25: return "f25";
    26: return "f26";
    27: return "f27";
    28: return "f28";
    29: return "f29";
    30: return "f30";
    31: return "f31";
    default: begin
          $error("ERROR: SystemVerilog Functional Coverage: get_fpr_name(%0s) not found fpr", key);
          $fatal(1);
      end
  endcase
endfunction

// Vector register number to string
function string get_vr_name(int key);
  case(key)
    0: return "v0";
    1: return "v1";
    2: return "v2";
    3: return "v3";
    4: return "v4";
    5: return "v5";
    6: return "v6";
    7: return "v7";
    8: return "v8";
    9: return "v9";
    10: return "v10";
    11: return "v11";
    12: return "v12";
    13: return "v13";
    14: return "v14";
    15: return "v15";
    16: return "v16";
    17: return "v17";
    18: return "v18";
    19: return "v19";
    20: return "v20";
    21: return "v21";
    22: return "v22";
    23: return "v23";
    24: return "v24";
    25: return "v25";
    26: return "v26";
    27: return "v27";
    28: return "v28";
    29: return "v29";
    30: return "v30";
    31: return "v31";
    default: begin
          $error("ERROR: SystemVerilog Functional Coverage: get_vr_name(%0s) not found vr", key);
          $fatal(1);
      end
  endcase
endfunction

// Compressed integer register number to string
function string get_c_gpr_name(int key);
  case(key)
`ifndef ABI_REG_NAMES
    0: return "x8";
    1: return "x9";
    2: return "x10";
    3: return "x11";
    4: return "x12";
    5: return "x13";
    6: return "x14";
    7: return "x15";
`else
    0: return "s0";
    1: return "s1";
    2: return "a0";
    3: return "a1";
    4: return "a2";
    5: return "a3";
    6: return "a4";
    7: return "a5";
`endif
    default: begin
          $error("ERROR: SystemVerilog Functional Coverage: get_c_gpr_name(%0s) not found compressed gpr", key);
          $fatal(1);
      end
  endcase
endfunction

// Compressed floating point register number to string
function string get_c_fpr_name(int key);
  case(key)
    0: return "f8";
    1: return "f9";
    2: return "f10";
    3: return "f11";
    4: return "f12";
    5: return "f13";
    6: return "f14";
    7: return "f15";
    default: begin
          $error("ERROR: SystemVerilog Functional Coverage: get_c_fpr_name(%0s) not found compressed fpr", key);
          $fatal(1);
      end
  endcase
endfunction

// Floating point rounding mode number to string
function string get_frm_string(int key);
  case(key)
    3'b000: return "rne";
    3'b001: return "rtz";
    3'b010: return "rdn";
    3'b011: return "rup";
    3'b100: return "rmm";
    3'b111: return "dyn";
    default: begin
          $display("SystemVerilog Functional Coverage: invalid rounding mode: %0d", key);
          return $sformatf("rm%0d", key); // return rounding mode number for invalid values for coverage purposes
      end
  endcase
endfunction

//Vector vsetvli parameters
function string get_vtype_eSEW_name(int eSEW);
  case(eSEW)
    3'b000: return "e8";
    3'b001: return "e16";
    3'b010: return "e32";
    3'b011: return "e64";

    default: return "reserved";
  endcase
endfunction

function string get_vtype_mLMUL_name(int mLMUL);
  case(mLMUL)
    3'b101: return "mf8";
    3'b110: return "mf4";
    3'b111: return "mf2";
    3'b000: return "m1";
    3'b001: return "m2";
    3'b010: return "m4";
    3'b011: return "m8";

    default: return "reserved";
  endcase
endfunction

function string get_vtype_ta_name(int ta);
  case(ta)
    1'b1: return "ta";
    1'b0: return "tu";
  endcase
endfunction

function string get_vtype_ma_name(int ma);
  case(ma)
    1'b1: return "ma";
    1'b0: return "mu";
  endcase
endfunction


// CSR number to string
function string get_csr_name(int key);
  import RISCV_decode_pkg::*;
  case(key)
    CSR_FFLAGS: return "fflags";
    CSR_FRM: return "frm";
    CSR_FCSR: return "fcsr";
    CSR_VSTART: return "vstart";
    CSR_VXSAT: return "vxsat";
    CSR_VXRM: return "vxrm";
    CSR_VCSR: return "vcsr";
    CSR_SSP: return "ssp";
    CSR_SEED: return "seed";
    CSR_JVT: return "jvt";
    CSR_CYCLE: return "cycle";
    CSR_TIME: return "time";
    CSR_INSTRET: return "instret";
    CSR_HPMCOUNTER3: return "hpmcounter3";
    CSR_HPMCOUNTER4: return "hpmcounter4";
    CSR_HPMCOUNTER5: return "hpmcounter5";
    CSR_HPMCOUNTER6: return "hpmcounter6";
    CSR_HPMCOUNTER7: return "hpmcounter7";
    CSR_HPMCOUNTER8: return "hpmcounter8";
    CSR_HPMCOUNTER9: return "hpmcounter9";
    CSR_HPMCOUNTER10: return "hpmcounter10";
    CSR_HPMCOUNTER11: return "hpmcounter11";
    CSR_HPMCOUNTER12: return "hpmcounter12";
    CSR_HPMCOUNTER13: return "hpmcounter13";
    CSR_HPMCOUNTER14: return "hpmcounter14";
    CSR_HPMCOUNTER15: return "hpmcounter15";
    CSR_HPMCOUNTER16: return "hpmcounter16";
    CSR_HPMCOUNTER17: return "hpmcounter17";
    CSR_HPMCOUNTER18: return "hpmcounter18";
    CSR_HPMCOUNTER19: return "hpmcounter19";
    CSR_HPMCOUNTER20: return "hpmcounter20";
    CSR_HPMCOUNTER21: return "hpmcounter21";
    CSR_HPMCOUNTER22: return "hpmcounter22";
    CSR_HPMCOUNTER23: return "hpmcounter23";
    CSR_HPMCOUNTER24: return "hpmcounter24";
    CSR_HPMCOUNTER25: return "hpmcounter25";
    CSR_HPMCOUNTER26: return "hpmcounter26";
    CSR_HPMCOUNTER27: return "hpmcounter27";
    CSR_HPMCOUNTER28: return "hpmcounter28";
    CSR_HPMCOUNTER29: return "hpmcounter29";
    CSR_HPMCOUNTER30: return "hpmcounter30";
    CSR_HPMCOUNTER31: return "hpmcounter31";
    CSR_VL: return "vl";
    CSR_VTYPE: return "vtype";
    CSR_VLENB: return "vlenb";
    CSR_SSTATUS: return "sstatus";
    CSR_SEDELEG: return "sedeleg";
    CSR_SIDELEG: return "sideleg";
    CSR_SIE: return "sie";
    CSR_STVEC: return "stvec";
    CSR_SCOUNTEREN: return "scounteren";
    CSR_SENVCFG: return "senvcfg";
    CSR_SSTATEEN0: return "sstateen0";
    CSR_SSTATEEN1: return "sstateen1";
    CSR_SSTATEEN2: return "sstateen2";
    CSR_SSTATEEN3: return "sstateen3";
    CSR_SCOUNTINHIBIT: return "scountinhibit";
    CSR_SSCRATCH: return "sscratch";
    CSR_SEPC: return "sepc";
    CSR_SCAUSE: return "scause";
    CSR_STVAL: return "stval";
    CSR_SIP: return "sip";
    CSR_STIMECMP: return "stimecmp";
    CSR_SCTRCTL: return "sctrctl";
    CSR_SCTRSTATUS: return "sctrstatus";
    CSR_SISELECT: return "siselect";
    CSR_SIREG: return "sireg";
    CSR_SIREG2: return "sireg2";
    CSR_SIREG3: return "sireg3";
    CSR_SIREG4: return "sireg4";
    CSR_SIREG5: return "sireg5";
    CSR_SIREG6: return "sireg6";
    CSR_STOPEI: return "stopei";
    CSR_SCTRDEPTH: return "sctrdepth";
    CSR_SATP: return "satp";
    CSR_SRMCFG: return "srmcfg";
    CSR_SCONTEXT: return "scontext";
    CSR_VSSTATUS: return "vsstatus";
    CSR_VSIE: return "vsie";
    CSR_VSTVEC: return "vstvec";
    CSR_VSSCRATCH: return "vsscratch";
    CSR_VSEPC: return "vsepc";
    CSR_VSCAUSE: return "vscause";
    CSR_VSTVAL: return "vstval";
    CSR_VSIP: return "vsip";
    CSR_VSTIMECMP: return "vstimecmp";
    CSR_VSCTRCTL: return "vsctrctl";
    CSR_VSISELECT: return "vsiselect";
    CSR_VSIREG: return "vsireg";
    CSR_VSIREG2: return "vsireg2";
    CSR_VSIREG3: return "vsireg3";
    CSR_VSIREG4: return "vsireg4";
    CSR_VSIREG5: return "vsireg5";
    CSR_VSIREG6: return "vsireg6";
    CSR_VSTOPEI: return "vstopei";
    CSR_VSATP: return "vsatp";
    CSR_HSTATUS: return "hstatus";
    CSR_HEDELEG: return "hedeleg";
    CSR_HIDELEG: return "hideleg";
    CSR_HIE: return "hie";
    CSR_HTIMEDELTA: return "htimedelta";
    CSR_HCOUNTEREN: return "hcounteren";
    CSR_HGEIE: return "hgeie";
    CSR_HVIEN: return "hvien";
    CSR_HVICTL: return "hvictl";
    CSR_HENVCFG: return "henvcfg";
    CSR_HSTATEEN0: return "hstateen0";
    CSR_HSTATEEN1: return "hstateen1";
    CSR_HSTATEEN2: return "hstateen2";
    CSR_HSTATEEN3: return "hstateen3";
    CSR_HTVAL: return "htval";
    CSR_HIP: return "hip";
    CSR_HVIP: return "hvip";
    CSR_HVIPRIO1: return "hviprio1";
    CSR_HVIPRIO2: return "hviprio2";
    CSR_HTINST: return "htinst";
    CSR_HGATP: return "hgatp";
    CSR_HCONTEXT: return "hcontext";
    CSR_HGEIP: return "hgeip";
    CSR_VSTOPI: return "vstopi";
    CSR_SCOUNTOVF: return "scountovf";
    CSR_STOPI: return "stopi";
    CSR_UTVT: return "utvt";
    CSR_UNXTI: return "unxti";
    CSR_UINTSTATUS: return "uintstatus";
    CSR_USCRATCHCSW: return "uscratchcsw";
    CSR_USCRATCHCSWL: return "uscratchcswl";
    CSR_STVT: return "stvt";
    CSR_SNXTI: return "snxti";
    CSR_SINTSTATUS: return "sintstatus";
    CSR_SSCRATCHCSW: return "sscratchcsw";
    CSR_SSCRATCHCSWL: return "sscratchcswl";
    CSR_MTVT: return "mtvt";
    CSR_MNXTI: return "mnxti";
    CSR_MINTSTATUS: return "mintstatus";
    CSR_MSCRATCHCSW: return "mscratchcsw";
    CSR_MSCRATCHCSWL: return "mscratchcswl";
    CSR_MSTATUS: return "mstatus";
    CSR_MISA: return "misa";
    CSR_MEDELEG: return "medeleg";
    CSR_MIDELEG: return "mideleg";
    CSR_MIE: return "mie";
    CSR_MTVEC: return "mtvec";
    CSR_MCOUNTEREN: return "mcounteren";
    CSR_MVIEN: return "mvien";
    CSR_MVIP: return "mvip";
    CSR_MENVCFG: return "menvcfg";
    CSR_MSTATEEN0: return "mstateen0";
    CSR_MSTATEEN1: return "mstateen1";
    CSR_MSTATEEN2: return "mstateen2";
    CSR_MSTATEEN3: return "mstateen3";
    CSR_MCOUNTINHIBIT: return "mcountinhibit";
    CSR_MSCRATCH: return "mscratch";
    CSR_MEPC: return "mepc";
    CSR_MCAUSE: return "mcause";
    CSR_MTVAL: return "mtval";
    CSR_MIP: return "mip";
    CSR_MTINST: return "mtinst";
    CSR_MTVAL2: return "mtval2";
    CSR_MCTRCTL: return "mctrctl";
    CSR_MISELECT: return "miselect";
    CSR_MIREG: return "mireg";
    CSR_MIREG2: return "mireg2";
    CSR_MIREG3: return "mireg3";
    CSR_MIREG4: return "mireg4";
    CSR_MIREG5: return "mireg5";
    CSR_MIREG6: return "mireg6";
    CSR_MTOPEI: return "mtopei";
    CSR_PMPCFG0: return "pmpcfg0";
    CSR_PMPCFG1: return "pmpcfg1";
    CSR_PMPCFG2: return "pmpcfg2";
    CSR_PMPCFG3: return "pmpcfg3";
    CSR_PMPCFG4: return "pmpcfg4";
    CSR_PMPCFG5: return "pmpcfg5";
    CSR_PMPCFG6: return "pmpcfg6";
    CSR_PMPCFG7: return "pmpcfg7";
    CSR_PMPCFG8: return "pmpcfg8";
    CSR_PMPCFG9: return "pmpcfg9";
    CSR_PMPCFG10: return "pmpcfg10";
    CSR_PMPCFG11: return "pmpcfg11";
    CSR_PMPCFG12: return "pmpcfg12";
    CSR_PMPCFG13: return "pmpcfg13";
    CSR_PMPCFG14: return "pmpcfg14";
    CSR_PMPCFG15: return "pmpcfg15";
    CSR_PMPADDR0: return "pmpaddr0";
    CSR_PMPADDR1: return "pmpaddr1";
    CSR_PMPADDR2: return "pmpaddr2";
    CSR_PMPADDR3: return "pmpaddr3";
    CSR_PMPADDR4: return "pmpaddr4";
    CSR_PMPADDR5: return "pmpaddr5";
    CSR_PMPADDR6: return "pmpaddr6";
    CSR_PMPADDR7: return "pmpaddr7";
    CSR_PMPADDR8: return "pmpaddr8";
    CSR_PMPADDR9: return "pmpaddr9";
    CSR_PMPADDR10: return "pmpaddr10";
    CSR_PMPADDR11: return "pmpaddr11";
    CSR_PMPADDR12: return "pmpaddr12";
    CSR_PMPADDR13: return "pmpaddr13";
    CSR_PMPADDR14: return "pmpaddr14";
    CSR_PMPADDR15: return "pmpaddr15";
    CSR_PMPADDR16: return "pmpaddr16";
    CSR_PMPADDR17: return "pmpaddr17";
    CSR_PMPADDR18: return "pmpaddr18";
    CSR_PMPADDR19: return "pmpaddr19";
    CSR_PMPADDR20: return "pmpaddr20";
    CSR_PMPADDR21: return "pmpaddr21";
    CSR_PMPADDR22: return "pmpaddr22";
    CSR_PMPADDR23: return "pmpaddr23";
    CSR_PMPADDR24: return "pmpaddr24";
    CSR_PMPADDR25: return "pmpaddr25";
    CSR_PMPADDR26: return "pmpaddr26";
    CSR_PMPADDR27: return "pmpaddr27";
    CSR_PMPADDR28: return "pmpaddr28";
    CSR_PMPADDR29: return "pmpaddr29";
    CSR_PMPADDR30: return "pmpaddr30";
    CSR_PMPADDR31: return "pmpaddr31";
    CSR_PMPADDR32: return "pmpaddr32";
    CSR_PMPADDR33: return "pmpaddr33";
    CSR_PMPADDR34: return "pmpaddr34";
    CSR_PMPADDR35: return "pmpaddr35";
    CSR_PMPADDR36: return "pmpaddr36";
    CSR_PMPADDR37: return "pmpaddr37";
    CSR_PMPADDR38: return "pmpaddr38";
    CSR_PMPADDR39: return "pmpaddr39";
    CSR_PMPADDR40: return "pmpaddr40";
    CSR_PMPADDR41: return "pmpaddr41";
    CSR_PMPADDR42: return "pmpaddr42";
    CSR_PMPADDR43: return "pmpaddr43";
    CSR_PMPADDR44: return "pmpaddr44";
    CSR_PMPADDR45: return "pmpaddr45";
    CSR_PMPADDR46: return "pmpaddr46";
    CSR_PMPADDR47: return "pmpaddr47";
    CSR_PMPADDR48: return "pmpaddr48";
    CSR_PMPADDR49: return "pmpaddr49";
    CSR_PMPADDR50: return "pmpaddr50";
    CSR_PMPADDR51: return "pmpaddr51";
    CSR_PMPADDR52: return "pmpaddr52";
    CSR_PMPADDR53: return "pmpaddr53";
    CSR_PMPADDR54: return "pmpaddr54";
    CSR_PMPADDR55: return "pmpaddr55";
    CSR_PMPADDR56: return "pmpaddr56";
    CSR_PMPADDR57: return "pmpaddr57";
    CSR_PMPADDR58: return "pmpaddr58";
    CSR_PMPADDR59: return "pmpaddr59";
    CSR_PMPADDR60: return "pmpaddr60";
    CSR_PMPADDR61: return "pmpaddr61";
    CSR_PMPADDR62: return "pmpaddr62";
    CSR_PMPADDR63: return "pmpaddr63";
    CSR_MSECCFG: return "mseccfg";
    CSR_TSELECT: return "tselect";
    CSR_TDATA1: return "tdata1";
    CSR_TDATA2: return "tdata2";
    CSR_TDATA3: return "tdata3";
    CSR_TINFO: return "tinfo";
    CSR_TCONTROL: return "tcontrol";
    CSR_MCONTEXT: return "mcontext";
    CSR_MSCONTEXT: return "mscontext";
    CSR_DCSR: return "dcsr";
    CSR_DPC: return "dpc";
    CSR_DSCRATCH0: return "dscratch0";
    CSR_DSCRATCH1: return "dscratch1";
    CSR_MCYCLE: return "mcycle";
    CSR_MINSTRET: return "minstret";
    CSR_MHPMCOUNTER3: return "mhpmcounter3";
    CSR_MHPMCOUNTER4: return "mhpmcounter4";
    CSR_MHPMCOUNTER5: return "mhpmcounter5";
    CSR_MHPMCOUNTER6: return "mhpmcounter6";
    CSR_MHPMCOUNTER7: return "mhpmcounter7";
    CSR_MHPMCOUNTER8: return "mhpmcounter8";
    CSR_MHPMCOUNTER9: return "mhpmcounter9";
    CSR_MHPMCOUNTER10: return "mhpmcounter10";
    CSR_MHPMCOUNTER11: return "mhpmcounter11";
    CSR_MHPMCOUNTER12: return "mhpmcounter12";
    CSR_MHPMCOUNTER13: return "mhpmcounter13";
    CSR_MHPMCOUNTER14: return "mhpmcounter14";
    CSR_MHPMCOUNTER15: return "mhpmcounter15";
    CSR_MHPMCOUNTER16: return "mhpmcounter16";
    CSR_MHPMCOUNTER17: return "mhpmcounter17";
    CSR_MHPMCOUNTER18: return "mhpmcounter18";
    CSR_MHPMCOUNTER19: return "mhpmcounter19";
    CSR_MHPMCOUNTER20: return "mhpmcounter20";
    CSR_MHPMCOUNTER21: return "mhpmcounter21";
    CSR_MHPMCOUNTER22: return "mhpmcounter22";
    CSR_MHPMCOUNTER23: return "mhpmcounter23";
    CSR_MHPMCOUNTER24: return "mhpmcounter24";
    CSR_MHPMCOUNTER25: return "mhpmcounter25";
    CSR_MHPMCOUNTER26: return "mhpmcounter26";
    CSR_MHPMCOUNTER27: return "mhpmcounter27";
    CSR_MHPMCOUNTER28: return "mhpmcounter28";
    CSR_MHPMCOUNTER29: return "mhpmcounter29";
    CSR_MHPMCOUNTER30: return "mhpmcounter30";
    CSR_MHPMCOUNTER31: return "mhpmcounter31";
    CSR_MCYCLECFG: return "mcyclecfg";
    CSR_MINSTRETCFG: return "minstretcfg";
    CSR_MHPMEVENT3: return "mhpmevent3";
    CSR_MHPMEVENT4: return "mhpmevent4";
    CSR_MHPMEVENT5: return "mhpmevent5";
    CSR_MHPMEVENT6: return "mhpmevent6";
    CSR_MHPMEVENT7: return "mhpmevent7";
    CSR_MHPMEVENT8: return "mhpmevent8";
    CSR_MHPMEVENT9: return "mhpmevent9";
    CSR_MHPMEVENT10: return "mhpmevent10";
    CSR_MHPMEVENT11: return "mhpmevent11";
    CSR_MHPMEVENT12: return "mhpmevent12";
    CSR_MHPMEVENT13: return "mhpmevent13";
    CSR_MHPMEVENT14: return "mhpmevent14";
    CSR_MHPMEVENT15: return "mhpmevent15";
    CSR_MHPMEVENT16: return "mhpmevent16";
    CSR_MHPMEVENT17: return "mhpmevent17";
    CSR_MHPMEVENT18: return "mhpmevent18";
    CSR_MHPMEVENT19: return "mhpmevent19";
    CSR_MHPMEVENT20: return "mhpmevent20";
    CSR_MHPMEVENT21: return "mhpmevent21";
    CSR_MHPMEVENT22: return "mhpmevent22";
    CSR_MHPMEVENT23: return "mhpmevent23";
    CSR_MHPMEVENT24: return "mhpmevent24";
    CSR_MHPMEVENT25: return "mhpmevent25";
    CSR_MHPMEVENT26: return "mhpmevent26";
    CSR_MHPMEVENT27: return "mhpmevent27";
    CSR_MHPMEVENT28: return "mhpmevent28";
    CSR_MHPMEVENT29: return "mhpmevent29";
    CSR_MHPMEVENT30: return "mhpmevent30";
    CSR_MHPMEVENT31: return "mhpmevent31";
    CSR_MVENDORID: return "mvendorid";
    CSR_MARCHID: return "marchid";
    CSR_MIMPID: return "mimpid";
    CSR_MHARTID: return "mhartid";
    CSR_MCONFIGPTR: return "mconfigptr";
    CSR_MTOPI: return "mtopi";
    CSR_SIEH: return "sieh";
    CSR_SIPH: return "siph";
    CSR_STIMECMPH: return "stimecmph";
    CSR_VSIEH: return "vsieh";
    CSR_VSIPH: return "vsiph";
    CSR_VSTIMECMPH: return "vstimecmph";
    CSR_HEDELEGH: return "hedelegh";
    CSR_HTIMEDELTAH: return "htimedeltah";
    CSR_HIDELEGH: return "hidelegh";
    CSR_HVIENH: return "hvienh";
    CSR_HENVCFGH: return "henvcfgh";
    CSR_HVIPH: return "hviph";
    CSR_HVIPRIO1H: return "hviprio1h";
    CSR_HVIPRIO2H: return "hviprio2h";
    CSR_HSTATEEN0H: return "hstateen0h";
    CSR_HSTATEEN1H: return "hstateen1h";
    CSR_HSTATEEN2H: return "hstateen2h";
    CSR_HSTATEEN3H: return "hstateen3h";
    CSR_CYCLEH: return "cycleh";
    CSR_TIMEH: return "timeh";
    CSR_INSTRETH: return "instreth";
    CSR_HPMCOUNTER3H: return "hpmcounter3h";
    CSR_HPMCOUNTER4H: return "hpmcounter4h";
    CSR_HPMCOUNTER5H: return "hpmcounter5h";
    CSR_HPMCOUNTER6H: return "hpmcounter6h";
    CSR_HPMCOUNTER7H: return "hpmcounter7h";
    CSR_HPMCOUNTER8H: return "hpmcounter8h";
    CSR_HPMCOUNTER9H: return "hpmcounter9h";
    CSR_HPMCOUNTER10H: return "hpmcounter10h";
    CSR_HPMCOUNTER11H: return "hpmcounter11h";
    CSR_HPMCOUNTER12H: return "hpmcounter12h";
    CSR_HPMCOUNTER13H: return "hpmcounter13h";
    CSR_HPMCOUNTER14H: return "hpmcounter14h";
    CSR_HPMCOUNTER15H: return "hpmcounter15h";
    CSR_HPMCOUNTER16H: return "hpmcounter16h";
    CSR_HPMCOUNTER17H: return "hpmcounter17h";
    CSR_HPMCOUNTER18H: return "hpmcounter18h";
    CSR_HPMCOUNTER19H: return "hpmcounter19h";
    CSR_HPMCOUNTER20H: return "hpmcounter20h";
    CSR_HPMCOUNTER21H: return "hpmcounter21h";
    CSR_HPMCOUNTER22H: return "hpmcounter22h";
    CSR_HPMCOUNTER23H: return "hpmcounter23h";
    CSR_HPMCOUNTER24H: return "hpmcounter24h";
    CSR_HPMCOUNTER25H: return "hpmcounter25h";
    CSR_HPMCOUNTER26H: return "hpmcounter26h";
    CSR_HPMCOUNTER27H: return "hpmcounter27h";
    CSR_HPMCOUNTER28H: return "hpmcounter28h";
    CSR_HPMCOUNTER29H: return "hpmcounter29h";
    CSR_HPMCOUNTER30H: return "hpmcounter30h";
    CSR_HPMCOUNTER31H: return "hpmcounter31h";
    CSR_MSTATUSH: return "mstatush";
    CSR_MIDELEGH: return "midelegh";
    CSR_MIEH: return "mieh";
    CSR_MVIENH: return "mvienh";
    CSR_MVIPH: return "mviph";
    CSR_MENVCFGH: return "menvcfgh";
    CSR_MSTATEEN0H: return "mstateen0h";
    CSR_MSTATEEN1H: return "mstateen1h";
    CSR_MSTATEEN2H: return "mstateen2h";
    CSR_MSTATEEN3H: return "mstateen3h";
    CSR_MIPH: return "miph";
    CSR_MCYCLECFGH: return "mcyclecfgh";
    CSR_MINSTRETCFGH: return "minstretcfgh";
    CSR_MHPMEVENT3H: return "mhpmevent3h";
    CSR_MHPMEVENT4H: return "mhpmevent4h";
    CSR_MHPMEVENT5H: return "mhpmevent5h";
    CSR_MHPMEVENT6H: return "mhpmevent6h";
    CSR_MHPMEVENT7H: return "mhpmevent7h";
    CSR_MHPMEVENT8H: return "mhpmevent8h";
    CSR_MHPMEVENT9H: return "mhpmevent9h";
    CSR_MHPMEVENT10H: return "mhpmevent10h";
    CSR_MHPMEVENT11H: return "mhpmevent11h";
    CSR_MHPMEVENT12H: return "mhpmevent12h";
    CSR_MHPMEVENT13H: return "mhpmevent13h";
    CSR_MHPMEVENT14H: return "mhpmevent14h";
    CSR_MHPMEVENT15H: return "mhpmevent15h";
    CSR_MHPMEVENT16H: return "mhpmevent16h";
    CSR_MHPMEVENT17H: return "mhpmevent17h";
    CSR_MHPMEVENT18H: return "mhpmevent18h";
    CSR_MHPMEVENT19H: return "mhpmevent19h";
    CSR_MHPMEVENT20H: return "mhpmevent20h";
    CSR_MHPMEVENT21H: return "mhpmevent21h";
    CSR_MHPMEVENT22H: return "mhpmevent22h";
    CSR_MHPMEVENT23H: return "mhpmevent23h";
    CSR_MHPMEVENT24H: return "mhpmevent24h";
    CSR_MHPMEVENT25H: return "mhpmevent25h";
    CSR_MHPMEVENT26H: return "mhpmevent26h";
    CSR_MHPMEVENT27H: return "mhpmevent27h";
    CSR_MHPMEVENT28H: return "mhpmevent28h";
    CSR_MHPMEVENT29H: return "mhpmevent29h";
    CSR_MHPMEVENT30H: return "mhpmevent30h";
    CSR_MHPMEVENT31H: return "mhpmevent31h";
    CSR_MNSCRATCH: return "mnscratch";
    CSR_MNEPC: return "mnepc";
    CSR_MNCAUSE: return "mncause";
    CSR_MNSTATUS: return "mnstatus";
    CSR_MSECCFGH: return "mseccfgh";
    CSR_MCYCLEH: return "mcycleh";
    CSR_MINSTRETH: return "minstreth";
    CSR_MHPMCOUNTER3H: return "mhpmcounter3h";
    CSR_MHPMCOUNTER4H: return "mhpmcounter4h";
    CSR_MHPMCOUNTER5H: return "mhpmcounter5h";
    CSR_MHPMCOUNTER6H: return "mhpmcounter6h";
    CSR_MHPMCOUNTER7H: return "mhpmcounter7h";
    CSR_MHPMCOUNTER8H: return "mhpmcounter8h";
    CSR_MHPMCOUNTER9H: return "mhpmcounter9h";
    CSR_MHPMCOUNTER10H: return "mhpmcounter10h";
    CSR_MHPMCOUNTER11H: return "mhpmcounter11h";
    CSR_MHPMCOUNTER12H: return "mhpmcounter12h";
    CSR_MHPMCOUNTER13H: return "mhpmcounter13h";
    CSR_MHPMCOUNTER14H: return "mhpmcounter14h";
    CSR_MHPMCOUNTER15H: return "mhpmcounter15h";
    CSR_MHPMCOUNTER16H: return "mhpmcounter16h";
    CSR_MHPMCOUNTER17H: return "mhpmcounter17h";
    CSR_MHPMCOUNTER18H: return "mhpmcounter18h";
    CSR_MHPMCOUNTER19H: return "mhpmcounter19h";
    CSR_MHPMCOUNTER20H: return "mhpmcounter20h";
    CSR_MHPMCOUNTER21H: return "mhpmcounter21h";
    CSR_MHPMCOUNTER22H: return "mhpmcounter22h";
    CSR_MHPMCOUNTER23H: return "mhpmcounter23h";
    CSR_MHPMCOUNTER24H: return "mhpmcounter24h";
    CSR_MHPMCOUNTER25H: return "mhpmcounter25h";
    CSR_MHPMCOUNTER26H: return "mhpmcounter26h";
    CSR_MHPMCOUNTER27H: return "mhpmcounter27h";
    CSR_MHPMCOUNTER28H: return "mhpmcounter28h";
    CSR_MHPMCOUNTER29H: return "mhpmcounter29h";
    CSR_MHPMCOUNTER30H: return "mhpmcounter30h";
    CSR_MHPMCOUNTER31H: return "mhpmcounter31h";
    default: return $sformatf("0x%0h", key);
  endcase
endfunction
