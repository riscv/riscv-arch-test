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

/*          To align with the starting address of a PMP region used in testing, the address is hardcoded here.
            Since the Sail data region begins at 0x80004000, we simply add the size of the test strings,
            which has been fixed at 4 KB. The executable blob each test places there begins at 80005000
            with a pad of return instructions, which is there to make sure we fetch a proper instruction
            from the background region; the region under test follows that pad.
 */
`ifdef UDB_MXLEN_64
  `define PMP_PAD_START      64'h80005000 // pad ahead of the region under test
  `define PMP_SPECIAL_REGION_START 64'h80005000 // Zicbo + Zaamo tests
  `define PMP_MASK_BASE      64'h4000
`else
  `define PMP_PAD_START      32'h80005000 // pad ahead of the region under test
  `define PMP_SPECIAL_REGION_START 32'h80005000 // Zicbo + Zaamo tests
  `define PMP_MASK_BASE      32'h4000
`endif

// Calculate region size g in bytes.
`define g_tor       (2 ** (`UDB_PMP_GRANULARITY))
`define g_napot     ((`UDB_PMP_GRANULARITY > 2) ? (2 ** (`UDB_PMP_GRANULARITY)) : (2 ** (`UDB_PMP_GRANULARITY + 1)))

// Region bases. Each test pads its blob by one grain so that the region under test starts on a
// grain-aligned boundary and the pad stays in the background region (the pad is emitted by
// PMP_TOR_REGION_BYTES and PMP_NAPOT_REGION_PAD_WORDS in tests/env/rvtest_pmp_macros.h). A TOR or
// NA4 region is padded by one g_tor and a NAPOT region by one g_napot, so both bases track the
// grain: at grain 2 they are 0x80005004 and 0x80005008, at grain 6 both are 0x80005040. A NAPOT
// base must be g_napot-aligned in particular, because `(base>>2)|trailing1s` would otherwise decode
// to a region that swallows the pad -> NAPOT tests hang / mis-cover.
`define PMP_REGION_START       (`PMP_PAD_START + `g_tor)   // generic (TOR/NA4) tests
`define PMP_NAPOT_REGION_START (`PMP_PAD_START + `g_napot)

// Calculate k = G - 1 trailing ones in NAPOT encoding.
`define k  ((`UDB_PMP_GRANULARITY > 3) ? (`UDB_PMP_GRANULARITY - 3) : 0)

// Address encodings

// TOR or NA4 region: directly right-shifted
`define NON_STANDARD_REGION  (`PMP_REGION_START >> 2)              // TOR/NA4 format: yyyyy...
`define SPECIAL_NON_STANDARD_REGION  (`PMP_SPECIAL_REGION_START >> 2)              // TOR/NA4 format: yyyyy...

// NAPOT region: add trailing 1s per `k` to form mask
`define STANDARD_REGION      ((`PMP_NAPOT_REGION_START >> 2) | ((2 ** `k) - 1)) // NAPOT format: yyyyy...0111
`define SPECIAL_STANDARD_REGION      ((`PMP_SPECIAL_REGION_START >> 2) | ((2 ** `k) - 1)) // NAPOT format: yyyyy...0111

// Code-size-invariant region matching. The region-under-test is placed by each test at a `.p2align 12`
// boundary inside .data, which the linker puts at ALIGN(0x4000) AFTER the variable-size .text.rvtest.
// So its ABSOLUTE address drifts with test code size (small tests -> 0x80005xxx, large tests such as
// cfg_XWR's 400-entry signature -> 0x80009xxx), but it always sits at the same offset within a
// 0x4000-aligned block -> its LOW address bits are invariant. Match pmp_hit and the region-address
// coverpoints on those low bits (byte address & 0x3FFF, or pmpaddr & 0xFFF) so coverage fires no matter
// where .data landed. pmpaddr values in these tests are sparse (region / 0 / all-ones), so the low-bit
// match has no false positives. Assumes the linker's .data ALIGN of 0x4000 (which the DUT/ref share).
`define PMP_ADDR_LOWMASK      (`PMP_MASK_BASE - 1)        // low 14 bits of a byte address
`define PMP_PMPADDR_LOWMASK   ((`PMP_MASK_BASE - 1) >> 2) // low 12 bits of a pmpaddr

// UDB_MXLEN_64 -> [53:0] & UDB_MXLEN_32 -> [31:0]
`define EFFECTIVE_PMPADDR (`ifdef UDB_MXLEN_64 53 `else 31 `endif)
`define READ_ZERO_MASK   ~((1<<(`UDB_PMP_GRANULARITY - 2))-1)


// -----------------------------------------------------------------------------
//                                 FLEN Macros
// -----------------------------------------------------------------------------

// XLEN/FLEN as usable numbers
`ifdef Q_COVERAGE
  `define FLEN 128
`elsif D_COVERAGE
  `define FLEN 64
`else
  `define FLEN 32
`endif

///////////////////////////////////////////////////
// VECTOR-RELATED MACROS
///////////////////////////////////////////////////

// MAXINDEXEEW — maximum supported index element width for indexed load/store
// Config should define one of: MAXINDEXEEW64, MAXINDEXEEW32, MAXINDEXEEW16, MAXINDEXEEW8
`ifdef MAXINDEXEEW64
  `define MAXINDEXEEW 64
  `define MAXINDEXEEW_GE8
  `define MAXINDEXEEW_GE16
  `define MAXINDEXEEW_GE32
  `define MAXINDEXEEW_GE64
`elsif MAXINDEXEEW32
  `define MAXINDEXEEW 32
  `define MAXINDEXEEW_GE8
  `define MAXINDEXEEW_GE16
  `define MAXINDEXEEW_GE32
`elsif MAXINDEXEEW16
  `define MAXINDEXEEW 16
  `define MAXINDEXEEW_GE8
  `define MAXINDEXEEW_GE16
`elsif MAXINDEXEEW8
  `define MAXINDEXEEW 8
  `define MAXINDEXEEW_GE8
`endif

// Set register type length
`define XLEN_BITS         bit        [`UDB_MXLEN-1:0]
`define SIGNED_XLEN_BITS  bit signed [`UDB_MXLEN-1:0]
`define FLEN_BITS         bit        [`FLEN-1:0]
`define SIGNED_FLEN_BITS  bit signed [`FLEN-1:0]
`define VLEN_BITS         bit        [VLEN-1:0]
`define SIGNED_VLEN_BITS  bit signed [VLEN-1:0]

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
`ifndef E_SUPPORTED
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
