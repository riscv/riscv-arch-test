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
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[62:58] {
                bins combo[] = {[0:31]};
                }
        `else
                // VSINH/VUINH (bits 59:58) hardwired 0 without H-ext -- only MINH/SINH/UINH vary
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[62:60] {
                bins combo[] = {[0:7]};
                }
        `endif
    `else
        `ifdef H_SUPPORTED
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[30:26] {
                bins combo[] = {[0:31]};
                }
        `else
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[30:28] {
                bins combo[] = {[0:7]};
                }
        `endif
    `endif

    `ifdef UDB_MXLEN_64
        `define OF_VEC {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent31", "mhpmevent31")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent30", "mhpmevent30")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent29", "mhpmevent29")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent28", "mhpmevent28")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent27", "mhpmevent27")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent26", "mhpmevent26")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent25", "mhpmevent25")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent24", "mhpmevent24")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent23", "mhpmevent23")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent22", "mhpmevent22")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent21", "mhpmevent21")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent20", "mhpmevent20")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent19", "mhpmevent19")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent18", "mhpmevent18")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent17", "mhpmevent17")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent16", "mhpmevent16")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent15", "mhpmevent15")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent14", "mhpmevent14")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent13", "mhpmevent13")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent12", "mhpmevent12")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent11", "mhpmevent11")[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent10", "mhpmevent10")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent9", "mhpmevent9")[63],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent8", "mhpmevent8")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent7", "mhpmevent7")[63],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent6", "mhpmevent6")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent5", "mhpmevent5")[63],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent4", "mhpmevent4")[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[63]}
    `else
        `define OF_VEC {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent31h", "mhpmevent31h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent30h", "mhpmevent30h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent29h", "mhpmevent29h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent28h", "mhpmevent28h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent27h", "mhpmevent27h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent26h", "mhpmevent26h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent25h", "mhpmevent25h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent24h", "mhpmevent24h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent23h", "mhpmevent23h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent22h", "mhpmevent22h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent21h", "mhpmevent21h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent20h", "mhpmevent20h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent19h", "mhpmevent19h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent18h", "mhpmevent18h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent17h", "mhpmevent17h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent16h", "mhpmevent16h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent15h", "mhpmevent15h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent14h", "mhpmevent14h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent13h", "mhpmevent13h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent12h", "mhpmevent12h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent11h", "mhpmevent11h")[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent10h", "mhpmevent10h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent9h", "mhpmevent9h")[31],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent8h", "mhpmevent8h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent7h", "mhpmevent7h")[31],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent6h", "mhpmevent6h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent5h", "mhpmevent5h")[31],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent4h", "mhpmevent4h")[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[31]}
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[62:58]) {
                bins none_set  = {5'b00000};
                bins msu_set   = {5'b11100};
                bins minh_only = {5'b10000};
                bins sinh_only = {5'b01000};
                bins uinh_only = {5'b00100};
        }
    `else
        // On RV32, MINH/SINH/UINH/VSINH/VUINH live in mhpmevent*h[30:26]
        mhpmevent_inhibits_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[30:26]) {
                bins none_set  = {5'b00000};
                bins msu_set   = {5'b11100};
                bins minh_only = {5'b10000};
                bins sinh_only = {5'b01000};
                bins uinh_only = {5'b00100};
        }
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_of: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[63] {}
        mhpmevent_of_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[63] {
                bins zero = {0};
        }
        mhpmevent_of_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")[63] {
                bins one = {1};
        }
    `else
        // On RV32, Sscofpmf bits (including OF) live in mhpmevent*h[31:28]
        mhpmevent_of: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[31] {}
        mhpmevent_of_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[31] {
                bins zero = {0};
        }
        mhpmevent_of_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h")[31] {
                bins one = {1};
        }
    `endif
    mip_clear: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mip", "mip") == 0) {
            bins yes = {1};
    }
    mie_clear: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mie", "mie") == 0) {
            bins yes = {1};
    }

    mhpmcounter_extreme_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmcounter3", "mhpmcounter3")) {
            bins all_ones  = {'1};
            bins all_zeros = {'0};
    }

    `ifdef UDB_MXLEN_64
        mhpmevent_all_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3") == '0) {
                bins yes = {1};
        }
    `else
        // On RV32 the 64-bit mhpmevent3 is split across mhpmevent3h:mhpmevent3
        mhpmevent_all_zero: coverpoint ({get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3h", "mhpmevent3h"), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mhpmevent3", "mhpmevent3")} == '0) {
                bins yes = {1};
        }
    `endif
