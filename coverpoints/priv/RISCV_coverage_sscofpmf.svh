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

    // helper coverpoints crossed by all three Sscofpmf covergroups; helpers only some of them
    // cross are defined in those covergroups
    `ifdef UDB_MXLEN_64
        `ifdef H_SUPPORTED
                mhpmevent_xinh_combos: coverpoint ins.current.csr[CSR_MHPMEVENT3][62:58] {
                bins combo[] = {[0:31]};
                }
        `else
                // VSINH/VUINH (bits 59:58) hardwired 0 without H-ext -- only MINH/SINH/UINH vary
                mhpmevent_xinh_combos: coverpoint ins.current.csr[CSR_MHPMEVENT3][62:60] {
                bins combo[] = {[0:7]};
                }
        `endif
    `else
        `ifdef H_SUPPORTED
                mhpmevent_xinh_combos: coverpoint ins.current.csr[CSR_MHPMEVENT3H][30:26] {
                bins combo[] = {[0:31]};
                }
        `else
                mhpmevent_xinh_combos: coverpoint ins.current.csr[CSR_MHPMEVENT3H][30:28] {
                bins combo[] = {[0:7]};
                }
        `endif
    `endif

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
        mhpmevent_inhibits_pattern_state: coverpoint (ins.current.csr[CSR_MHPMEVENT3][62:58]) {
                bins none_set  = {5'b00000};
                bins msu_set   = {5'b11100};
                bins minh_only = {5'b10000};
                bins sinh_only = {5'b01000};
                bins uinh_only = {5'b00100};
        }
    `else
        // On RV32, MINH/SINH/UINH/VSINH/VUINH live in mhpmevent*h[30:26]
        mhpmevent_inhibits_pattern_state: coverpoint (ins.current.csr[CSR_MHPMEVENT3H][30:26]) {
                bins none_set  = {5'b00000};
                bins msu_set   = {5'b11100};
                bins minh_only = {5'b10000};
                bins sinh_only = {5'b01000};
                bins uinh_only = {5'b00100};
        }
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_of: coverpoint ins.current.csr[CSR_MHPMEVENT3][63] {}
        mhpmevent_of_zero: coverpoint ins.current.csr[CSR_MHPMEVENT3][63] {
                bins zero = {0};
        }
        mhpmevent_of_one: coverpoint ins.current.csr[CSR_MHPMEVENT3][63] {
                bins one = {1};
        }
    `else
        // On RV32, Sscofpmf bits (including OF) live in mhpmevent*h[31:28]
        mhpmevent_of: coverpoint ins.current.csr[CSR_MHPMEVENT3H][31] {}
        mhpmevent_of_zero: coverpoint ins.current.csr[CSR_MHPMEVENT3H][31] {
                bins zero = {0};
        }
        mhpmevent_of_one: coverpoint ins.current.csr[CSR_MHPMEVENT3H][31] {
                bins one = {1};
        }
    `endif
    mip_clear: coverpoint (ins.current.csr[CSR_MIP] == 0) {
            bins yes = {1};
    }
    mie_clear: coverpoint (ins.current.csr[CSR_MIE] == 0) {
            bins yes = {1};
    }

    mhpmcounter_extreme_state: coverpoint (ins.current.csr[CSR_MHPMCOUNTER3]) {
            bins all_ones  = {'1};
            bins all_zeros = {'0};
    }

    `ifdef UDB_MXLEN_64
        mhpmevent_all_zero: coverpoint (ins.current.csr[CSR_MHPMEVENT3] == '0) {
                bins yes = {1};
        }
    `else
        // On RV32 the 64-bit mhpmevent3 is split across mhpmevent3h:mhpmevent3
        mhpmevent_all_zero: coverpoint ({ins.current.csr[CSR_MHPMEVENT3H], ins.current.csr[CSR_MHPMEVENT3]} == '0) {
                bins yes = {1};
        }
    `endif
