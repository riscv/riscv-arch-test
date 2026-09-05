///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written by Ayesha Anwar ayesha.anwaar2005@gmail.com
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////


    // helper coverpoints for the Sscofpmf extension
    csr_access_pattern: coverpoint ins.current.insn {
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0);
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1);
        wildcard bins csrrs1    = {CSRRS} iff (ins.current.rs1_val == '1);
        wildcard bins csrrc1    = {CSRRC} iff (ins.current.rs1_val == '1);
        wildcard bins read_only = {CSRRS} iff (ins.current.rs1_val ==  0);
   }

    // Pack the 29 OF bits (mhpmevent3..mhpmevent31) into one expression via macro
    // NOTE: must be defined before any coverpoint below that uses `OF_VEC
    `ifdef UDB_MXLEN_64
        `define OF_VEC {ins.current.csr[CSR_MHPMEVENT31][63], ins.current.csr[CSR_MHPMEVENT30][63], \
                     ins.current.csr[CSR_MHPMEVENT29][63], ins.current.csr[CSR_MHPMEVENT28][63], \
                     ins.current.csr[CSR_MHPMEVENT27][63], ins.current.csr[CSR_MHPMEVENT26][63], \
                     ins.current.csr[CSR_MHPMEVENT25][63], ins.current.csr[CSR_MHPMEVENT24][63], \
                     ins.current.csr[CSR_MHPMEVENT23][63], ins.current.csr[CSR_MHPMEVENT22][63], \
                     ins.current.csr[CSR_MHPMEVENT21][63], ins.current.csr[CSR_MHPMEVENT20][63], \
                     ins.current.csr[CSR_MHPMEVENT19][63], ins.current.csr[CSR_MHPMEVENT18][63], \
                     ins.current.csr[CSR_MHPMEVENT17][63], ins.current.csr[CSR_MHPMEVENT16][63], \
                     ins.current.csr[CSR_MHPMEVENT15][63], ins.current.csr[CSR_MHPMEVENT14][63], \
                     ins.current.csr[CSR_MHPMEVENT13][63], ins.current.csr[CSR_MHPMEVENT12][63], \
                     ins.current.csr[CSR_MHPMEVENT11][63], ins.current.csr[CSR_MHPMEVENT10][63], \
                     ins.current.csr[CSR_MHPMEVENT9][63],  ins.current.csr[CSR_MHPMEVENT8][63], \
                     ins.current.csr[CSR_MHPMEVENT7][63],  ins.current.csr[CSR_MHPMEVENT6][63], \
                     ins.current.csr[CSR_MHPMEVENT5][63],  ins.current.csr[CSR_MHPMEVENT4][63], \
                     ins.current.csr[CSR_MHPMEVENT3][63]}
    `else
        `define OF_VEC {ins.current.csr[CSR_MHPMEVENT31H][31], ins.current.csr[CSR_MHPMEVENT30H][31], \
                     ins.current.csr[CSR_MHPMEVENT29H][31], ins.current.csr[CSR_MHPMEVENT28H][31], \
                     ins.current.csr[CSR_MHPMEVENT27H][31], ins.current.csr[CSR_MHPMEVENT26H][31], \
                     ins.current.csr[CSR_MHPMEVENT25H][31], ins.current.csr[CSR_MHPMEVENT24H][31], \
                     ins.current.csr[CSR_MHPMEVENT23H][31], ins.current.csr[CSR_MHPMEVENT22H][31], \
                     ins.current.csr[CSR_MHPMEVENT21H][31], ins.current.csr[CSR_MHPMEVENT20H][31], \
                     ins.current.csr[CSR_MHPMEVENT19H][31], ins.current.csr[CSR_MHPMEVENT18H][31], \
                     ins.current.csr[CSR_MHPMEVENT17H][31], ins.current.csr[CSR_MHPMEVENT16H][31], \
                     ins.current.csr[CSR_MHPMEVENT15H][31], ins.current.csr[CSR_MHPMEVENT14H][31], \
                     ins.current.csr[CSR_MHPMEVENT13H][31], ins.current.csr[CSR_MHPMEVENT12H][31], \
                     ins.current.csr[CSR_MHPMEVENT11H][31], ins.current.csr[CSR_MHPMEVENT10H][31], \
                     ins.current.csr[CSR_MHPMEVENT9H][31],  ins.current.csr[CSR_MHPMEVENT8H][31], \
                     ins.current.csr[CSR_MHPMEVENT7H][31],  ins.current.csr[CSR_MHPMEVENT6H][31], \
                     ins.current.csr[CSR_MHPMEVENT5H][31],  ins.current.csr[CSR_MHPMEVENT4H][31], \
                     ins.current.csr[CSR_MHPMEVENT3H][31]}
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_pattern: coverpoint ins.current.insn {
                wildcard bins none_set  = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val[62:58] == 5'b00000);
                wildcard bins msu_set   = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val[62:58] == 5'b11100);
                wildcard bins minh_only = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val[62:58] == 5'b10000);
                wildcard bins sinh_only = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val[62:58] == 5'b01000);
                wildcard bins uinh_only = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val[62:58] == 5'b00100);
        }
        `else
        // On RV32, MINH/SINH/UINH/VSINH/VUINH live in mhpmevent*h[30:26] (address + 0x400)
        mhpmevent_inhibits_pattern: coverpoint ins.current.insn {
                wildcard bins none_set  = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 + 12'h400 && ins.current.rs1_val[30:26] == 5'b00000);
                wildcard bins msu_set   = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 + 12'h400 && ins.current.rs1_val[30:26] == 5'b11100);
                wildcard bins minh_only = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 + 12'h400 && ins.current.rs1_val[30:26] == 5'b10000);
                wildcard bins sinh_only = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 + 12'h400 && ins.current.rs1_val[30:26] == 5'b01000);
                wildcard bins uinh_only = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 + 12'h400 && ins.current.rs1_val[30:26] == 5'b00100);
        }
    `endif
    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_all_zeros: coverpoint ins.current.insn {
                wildcard bins write_pattern = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val[62:58] == 5'b00000);
        }
    `else
        // On RV32, MINH/SINH/UINH/VSINH/VUINH live in mhpmevent*h[30:26] (address + 0x400)
        mhpmevent_inhibits_all_zeros: coverpoint ins.current.insn {
                wildcard bins write_pattern = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 + 12'h400 && ins.current.rs1_val[30:26] == 5'b00000);
        }
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_of: coverpoint ins.current.csr[CSR_MHPMEVENT3][63] {}
        mhpmevent_of_zero: coverpoint ins.current.csr[CSR_MHPMEVENT3][63] {
                bins zero = {0};
        }
    `else
        // On RV32, Sscofpmf bits (including OF) live in mhpmevent*h[31:28] (CSR address + 0x400)
        mhpmevent_of: coverpoint ins.current.csr[CSR_MHPMEVENT3 + 12'h400][31] {}
        mhpmevent_of_zero: coverpoint ins.current.csr[CSR_MHPMEVENT3 + 12'h400][31] {
                bins zero = {0};
        }
    `endif
    sip_lcofi: coverpoint ins.current.csr[CSR_SIP][13] {}
    sie_lcofi: coverpoint ins.current.csr[CSR_SIE][13] {}
    hpmcounter_nonzero: coverpoint (ins.current.csr[CSR_MHPMCOUNTER3] != 0) {}
    mip_clear: coverpoint (ins.current.csr[CSR_MIP] == 0) {
            bins yes = {1};
    }
    mie_clear: coverpoint (ins.current.csr[CSR_MIE] == 0) {
            bins yes = {1};
    }
    mhpmcounter_write_extremes: coverpoint ins.current.insn {
        wildcard bins write_ones  = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMCOUNTER3 && ins.current.rs1_val == '1);
        wildcard bins write_zeros = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMCOUNTER3 && ins.current.rs1_val == '0);
   }

    of_walking_one: coverpoint $clog2(`OF_VEC) iff ($onehot(`OF_VEC)) {
            bins b_of[] = {[0:28]};  // one bin per OF bit position (mhpmevent3..mhpmevent31 = 29 bits)
    }
    of_pattern_class: coverpoint $countones(`OF_VEC) {
            bins all_zeros   = {0};
            bins all_ones    = {29};
    }

    mcounteren_write_all_ones: coverpoint ins.current.insn {
                wildcard bins write_ones = {CSRRW} iff (ins.current.insn[31:20] == CSR_MCOUNTEREN &&
                                                  ins.current.rs1_val[31:3] == '1);
    }
    mcounteren_walking_one: coverpoint $clog2(ins.current.rs1_val[31:3])
        iff (ins.current.insn[31:20] == CSR_MCOUNTEREN && (ins.current.insn ==? CSRRW || ins.current.insn ==? CSRRS || ins.current.insn ==? CSRRC) && $onehot(ins.current.rs1_val[31:3])) {
                bins pos[] = {[0:28]};
}

    scountovf_of_match: coverpoint ((ins.current.csr[CSR_SCOUNTOVF][31:3] & ins.current.csr[CSR_MCOUNTEREN][31:3]) == (`OF_VEC & ins.current.csr[CSR_MCOUNTEREN][31:3])) {
            bins match = {1};
    }

    of_write_pattern: coverpoint (`OF_VEC) {
            bins all_ones     = {29'h1FFFFFFF};
            bins checker_even = {29'b1_0101_0101_0101_0101_0101_0101_0101}; // even-indexed OF bits set
            bins checker_odd  = {29'b0_1010_1010_1010_1010_1010_1010_1010}; // odd-indexed OF bits set
    }
    mcounteren_write_pattern: coverpoint $countones(ins.current.rs1_val[31:3])
                        iff (ins.current.insn[31:20] == CSR_MCOUNTEREN && (ins.current.insn ==? CSRRW || ins.current.insn ==? CSRRS || ins.current.insn ==? CSRRC)) {
            bins all_zeros   = {0};
            bins walking_one = {1};
            bins all_ones    = {29};
    }

    `ifdef UDB_MXLEN_64
        mhpmevent_all_zero: coverpoint ins.current.insn {
                wildcard bins write_zero = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val == '0);
        }
    `else
        mhpmevent_all_zero: coverpoint ins.current.insn {
                wildcard bins write_zero = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 + 12'h400 && ins.current.rs1_val == '0);
        }
        mhpmevent_base_zero: coverpoint ins.current.insn {
            wildcard bins write_zero = {CSRRW} iff (ins.current.insn[31:20] == CSR_MHPMEVENT3 && ins.current.rs1_val == '0);
    }
    `endif

    csrops: coverpoint ins.current.insn {
            wildcard bins csrw = {CSRRW};
            wildcard bins csrs = {CSRRS};
            wildcard bins csrc = {CSRRC};
    }

    hpm_csr_target: coverpoint ins.current.insn[31:20] {
            bins scountovf   = {CSR_SCOUNTOVF};
            `ifdef UDB_MXLEN_32
                bins mhpmevent[] = {CSR_MHPMEVENT3H,  CSR_MHPMEVENT4H,  CSR_MHPMEVENT5H,
                                CSR_MHPMEVENT6H,  CSR_MHPMEVENT7H,  CSR_MHPMEVENT8H,
                                CSR_MHPMEVENT9H,  CSR_MHPMEVENT10H, CSR_MHPMEVENT11H,
                                CSR_MHPMEVENT12H, CSR_MHPMEVENT13H, CSR_MHPMEVENT14H,
                                CSR_MHPMEVENT15H, CSR_MHPMEVENT16H, CSR_MHPMEVENT17H,
                                CSR_MHPMEVENT18H, CSR_MHPMEVENT19H, CSR_MHPMEVENT20H,
                                CSR_MHPMEVENT21H, CSR_MHPMEVENT22H, CSR_MHPMEVENT23H,
                                CSR_MHPMEVENT24H, CSR_MHPMEVENT25H, CSR_MHPMEVENT26H,
                                CSR_MHPMEVENT27H, CSR_MHPMEVENT28H, CSR_MHPMEVENT29H,
                                CSR_MHPMEVENT30H, CSR_MHPMEVENT31H};
             `endif
    }
    lcofi_ip_one: coverpoint ins.current.csr[CSR_MIP][13] {
            bins one  = {1};
    }
    lcofi_ip_zero: coverpoint ins.current.csr[CSR_MIP][13] {
            bins zero = {0};
    }
    lcofi_ip: coverpoint ins.current.csr[CSR_MIP][13] {}
    lcofi_ie:      coverpoint ins.current.csr[CSR_MIE][13] {}
    lcofi_mideleg: coverpoint ins.current.csr[CSR_MIDELEG][13] {}
    lcofi_mideleg_one: coverpoint ins.current.csr[CSR_MIDELEG][13] {
            bins one  = {1};
    }
    lcofi_mideleg_zero: coverpoint ins.current.csr[CSR_MIDELEG][13] {
            bins zero = {0};
    }
    mstatus_mie_clear: coverpoint ins.current.csr[CSR_MSTATUS][3] {
            bins zero = {0};
    }
    mstatus_mie_set: coverpoint ins.current.csr[CSR_MSTATUS][3] {
            bins one = {1};
    }
    mstatus_sie_set: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins one = {1};
    }
    sstatus_sie_set: coverpoint ins.current.csr[CSR_SSTATUS][1] {
            bins one = {1};
    }
    mip_other_pending: coverpoint {ins.current.csr[CSR_MIP][11], ins.current.csr[CSR_MIP][7], ins.current.csr[CSR_MIP][3],
                                    ins.current.csr[CSR_MIP][9],  ins.current.csr[CSR_MIP][5], ins.current.csr[CSR_MIP][1]} {
            bins none = {6'b000000};
            bins meip = {6'b100000};
            bins mtip = {6'b010000};
            bins msip = {6'b001000};
            bins seip = {6'b000100};
            bins stip = {6'b000010};
            bins ssip = {6'b000001};
    }
