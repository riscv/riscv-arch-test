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
    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_all_set: coverpoint ins.current.insn {
                wildcard bins write_pattern = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT && ins.current.rs1_val[62:58] == 5'b11100);
        }
    `else
        // On RV32, MINH/SINH/UINH/VSINH/VUINH live in mhpmevent*h[30:26] (address + 0x400)
        mhpmevent_inhibits_all_set: coverpoint ins.current.insn {
                wildcard bins write_pattern = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT + 12'h400 && ins.current.rs1_val[30:26] == 5'b11100);
        }
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_of: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][63] {}
        mhpmevent_of_zero: coverpoint ins.current.csr[RVMODEL_MHPMEVENT][63] {
                bins zero = {0};
        }
    `else
        // On RV32, Sscofpmf bits (including OF) live in mhpmevent*h[31:28] (CSR address + 0x400)
        mhpmevent_of: coverpoint ins.current.csr[RVMODEL_MHPMEVENT + 12'h400][31] {}
        mhpmevent_of_zero: coverpoint ins.current.csr[RVMODEL_MHPMEVENT + 12'h400][31] {
                bins zero = {0};
        }
    `endif
    sip_lcofi: coverpoint ins.current.csr[CSR_SIP][13] {}
    sie_lcofi: coverpoint ins.current.csr[CSR_SIE][13] {}
    hpmcounter_nonzero: coverpoint (ins.current.csr[RVMODEL_MHPMCOUNTER] != 0) {}
    mip_clear: coverpoint (ins.current.csr[CSR_MIP] == 0) {
            bins yes = {1};
    }
    mie_clear: coverpoint (ins.current.csr[CSR_MIE] == 0) {
            bins yes = {1};
    }
    mhpmcounter_write_extremes: coverpoint ins.current.insn {
        wildcard bins write_ones  = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMCOUNTER && ins.current.rs1_val == '1);
        wildcard bins write_zeros = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMCOUNTER && ins.current.rs1_val == '0);
   }

    // Pack the 29 OF bits (mhpmevent3..mhpmevent31) into one expression via macro
    `ifdef UDB_MXLEN_64
        `define OF_VEC {ins.current.csr[CSR_MHPMEVENTH31][63], ins.current.csr[CSR_MHPMEVENTH30][63], \
                     ins.current.csr[CSR_MHPMEVENTH29][63], ins.current.csr[CSR_MHPMEVENTH28][63], \
                     ins.current.csr[CSR_MHPMEVENTH27][63], ins.current.csr[CSR_MHPMEVENTH26][63], \
                     ins.current.csr[CSR_MHPMEVENTH25][63], ins.current.csr[CSR_MHPMEVENTH24][63], \
                     ins.current.csr[CSR_MHPMEVENTH23][63], ins.current.csr[CSR_MHPMEVENTH22][63], \
                     ins.current.csr[CSR_MHPMEVENTH21][63], ins.current.csr[CSR_MHPMEVENTH20][63], \
                     ins.current.csr[CSR_MHPMEVENTH19][63], ins.current.csr[CSR_MHPMEVENTH18][63], \
                     ins.current.csr[CSR_MHPMEVENTH17][63], ins.current.csr[CSR_MHPMEVENTH16][63], \
                     ins.current.csr[CSR_MHPMEVENTH15][63], ins.current.csr[CSR_MHPMEVENTH14][63], \
                     ins.current.csr[CSR_MHPMEVENTH13][63], ins.current.csr[CSR_MHPMEVENTH12][63], \
                     ins.current.csr[CSR_MHPMEVENTH11][63], ins.current.csr[CSR_MHPMEVENTH10][63], \
                     ins.current.csr[CSR_MHPMEVENTH9][63],  ins.current.csr[CSR_MHPMEVENTH8][63], \
                     ins.current.csr[CSR_MHPMEVENTH7][63],  ins.current.csr[CSR_MHPMEVENTH6][63], \
                     ins.current.csr[CSR_MHPMEVENTH5][63],  ins.current.csr[CSR_MHPMEVENTH4][63], \
                     ins.current.csr[CSR_MHPMEVENTH3][63]}
    `else
        `define OF_VEC {ins.current.csr[CSR_MHPMEVENT31][31], ins.current.csr[CSR_MHPMEVENTH30][31], \
                     ins.current.csr[CSR_MHPMEVENTH29][31], ins.current.csr[CSR_MHPMEVENTH28][31], \
                     ins.current.csr[CSR_MHPMEVENTH27][31], ins.current.csr[CSR_MHPMEVENTH26][31], \
                     ins.current.csr[CSR_MHPMEVENTH25][31], ins.current.csr[CSR_MHPMEVENTH24][31], \
                     ins.current.csr[CSR_MHPMEVENTH23][31], ins.current.csr[CSR_MHPMEVENTH22][31], \
                     ins.current.csr[CSR_MHPMEVENTH21][31], ins.current.csr[CSR_MHPMEVENTH20][31], \
                     ins.current.csr[CSR_MHPMEVENTH19][31], ins.current.csr[CSR_MHPMEVENTH18][31], \
                     ins.current.csr[CSR_MHPMEVENTH17][31], ins.current.csr[CSR_MHPMEVENTH16][31], \
                     ins.current.csr[CSR_MHPMEVENTH15][31], ins.current.csr[CSR_MHPMEVENTH14][31], \
                     ins.current.csr[CSR_MHPMEVENTH13][31], ins.current.csr[CSR_MHPMEVENTH12][31], \
                     ins.current.csr[CSR_MHPMEVENTH11][31], ins.current.csr[CSR_MHPMEVENTH10][31], \
                     ins.current.csr[CSR_MHPMEVENTH9][31],  ins.current.csr[CSR_MHPMEVENTH8][31], \
                     ins.current.csr[CSR_MHPMEVENTH7][31],  ins.current.csr[CSR_MHPMEVENTH6][31], \
                     ins.current.csr[CSR_MHPMEVENTH5][31],  ins.current.csr[CSR_MHPMEVENTH4][31], \
                     ins.current.csr[CSR_MHPMEVENTH3][31]}
    `endif
    mcounteren_write_all_ones: coverpoint ins.current.insn {
                wildcard bins write_ones = {CSRRW} iff (ins.current.insn[31:20] == CSR_MCOUNTEREN &&
                                                  ins.current.rs1_val[31:3] == '1);
    }
    mcounteren_walking_one: coverpoint $clog2(ins.current.rs1_val[31:3])
        iff (ins.current.insn[31:20] == CSR_MCOUNTEREN && (ins.current.insn ==? CSRRW || ins.current.insn ==? CSRRS || ins.current.insn ==? CSRRC) && $onehot(ins.current.rs1_val[31:3])) {
                bins pos[] = {[0:28]};
}
    of_walking_one: coverpoint $clog2(`OF_VEC) iff ($onehot(`OF_VEC)) {
            bins b_of[] = {[0:28]};  // one bin per OF bit position (mhpmevent3..mhpmevent31 = 29 bits)
    }
    of_pattern_class: coverpoint $countones(`OF_VEC) {
            bins all_zeros   = {0};
            bins all_ones    = {29};
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
                wildcard bins write_zero = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT && ins.current.rs1_val == '0);
        }
    `else
        mhpmevent_all_zero: coverpoint ins.current.insn {
                wildcard bins write_zero = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT + 12'h400 && ins.current.rs1_val == '0);
        }
        mhpmevent_base_zero: coverpoint ins.current.insn {
            wildcard bins write_zero = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT && ins.current.rs1_val == '0);
    }
    `endif

    csrops: coverpoint ins.current.insn {
            wildcard bins csrw = {CSRRW};
            wildcard bins csrs = {CSRRS};
            wildcard bins csrc = {CSRRC};
    }

    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_all_set: coverpoint ins.current.insn {
                wildcard bins write_pattern = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT && ins.current.rs1_val[62:58] == 5'b11100);
        }
    `else
        // On RV32, MINH/SINH/UINH/VSINH/VUINH live in mhpmevent*h[30:26] (address + 0x400)
        mhpmevent_inhibits_all_set: coverpoint ins.current.insn {
                wildcard bins write_pattern = {CSRRW} iff (ins.current.insn[31:20] == RVMODEL_MHPMEVENT + 12'h400 && ins.current.rs1_val[30:26] == 5'b11100);
        }
    `endif

    hpm_csr_target: coverpoint ins.current.insn[31:20] {
            bins scountovf   = {CSR_SCOUNTOVF};
            bins mhpmevent[] = {CSR_MHPMEVENTH3,  CSR_MHPMEVENTH4,  CSR_MHPMEVENTH5,
                                CSR_MHPMEVENTH6,  CSR_MHPMEVENTH7,  CSR_MHPMEVENTH8,
                                CSR_MHPMEVENTH9,  CSR_MHPMEVENTH10, CSR_MHPMEVENTH11,
                                CSR_MHPMEVENTH12, CSR_MHPMEVENTH13, CSR_MHPMEVENTH14,
                                CSR_MHPMEVENTH15, CSR_MHPMEVENTH16, CSR_MHPMEVENTH17,
                                CSR_MHPMEVENTH18, CSR_MHPMEVENTH19, CSR_MHPMEVENTH20,
                                CSR_MHPMEVENTH21, CSR_MHPMEVENTH22, CSR_MHPMEVENTH23,
                                CSR_MHPMEVENTH24, CSR_MHPMEVENTH25, CSR_MHPMEVENTH26,
                                CSR_MHPMEVENTH27, CSR_MHPMEVENTH28, CSR_MHPMEVENTH29,
                                CSR_MHPMEVENTH30, CSR_MHPMEVENTH31};
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
    mstatus_sie_set: coverpoint ins.current.csr[CSR_MSTATUS][1] {
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
