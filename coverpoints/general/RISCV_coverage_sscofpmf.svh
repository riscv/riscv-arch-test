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

    // CSR addresses and width of the counter selected by RVMODEL_HPM_COUNTER (from rvmodel_macros.svh)
    `ifndef SSCOFPMF_MHPMEVENT
        `define SSCOFPMF_CSR_(base, n)  CSR_``base``n
        `define SSCOFPMF_CSR(base, n)   `SSCOFPMF_CSR_(base, n)
        `define SSCOFPMF_CSRH_(base, n) CSR_``base``n``H
        `define SSCOFPMF_CSRH(base, n)  `SSCOFPMF_CSRH_(base, n)
        `define SSCOFPMF_WIDTH_(n)      `UDB_HPM_COUNTER``n``_WIDTH
        `define SSCOFPMF_WIDTH(n)       `SSCOFPMF_WIDTH_(n)
        `define SSCOFPMF_MHPMEVENT      `SSCOFPMF_CSR(MHPMEVENT, `RVMODEL_HPM_COUNTER)
        `define SSCOFPMF_MHPMEVENTH     `SSCOFPMF_CSRH(MHPMEVENT, `RVMODEL_HPM_COUNTER)
        `define SSCOFPMF_MHPMCOUNTER    `SSCOFPMF_CSR(MHPMCOUNTER, `RVMODEL_HPM_COUNTER)
        `define SSCOFPMF_MHPMCOUNTERH   `SSCOFPMF_CSRH(MHPMCOUNTER, `RVMODEL_HPM_COUNTER)
        // A counter preset to all 1s holds 2^width - 1
        `define SSCOFPMF_COUNTER_MAX    ((64'd1 << `SSCOFPMF_WIDTH(`RVMODEL_HPM_COUNTER)) - 64'd1)
    `endif
    `ifdef UDB_MXLEN_64
        `ifdef H_SUPPORTED
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT)[62:58] {
                bins combo[] = {[0:31]};
                }
        `else
                // VSINH/VUINH (bits 59:58) hardwired 0 without H-ext -- only MINH/SINH/UINH vary
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT)[62:60] {
                bins combo[] = {[0:7]};
                }
        `endif
    `else
        `ifdef H_SUPPORTED
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH)[30:26] {
                bins combo[] = {[0:31]};
                }
        `else
                mhpmevent_xinh_combos: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH)[30:28] {
                bins combo[] = {[0:7]};
                }
        `endif
    `endif

    `ifdef UDB_MXLEN_64
        `define OF_VEC {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT31)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT30)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT29)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT28)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT27)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT26)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT25)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT24)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT23)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT22)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT21)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT20)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT19)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT18)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT17)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT16)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT15)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT14)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT13)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT12)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT11)[63], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT10)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT9)[63],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT8)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT7)[63],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT6)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT5)[63],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT4)[63], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT3)[63]}
    `else
        `define OF_VEC {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT31H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT30H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT29H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT28H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT27H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT26H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT25H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT24H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT23H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT22H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT21H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT20H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT19H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT18H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT17H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT16H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT15H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT14H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT13H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT12H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT11H)[31], get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT10H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT9H)[31],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT8H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT7H)[31],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT6H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT5H)[31],  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT4H)[31], \
                     get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MHPMEVENT3H)[31]}
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_inhibits_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT)[62:58]) {
                bins none_set  = {5'b00000};
                bins msu_set   = {5'b11100};
                bins minh_only = {5'b10000};
                bins sinh_only = {5'b01000};
                bins uinh_only = {5'b00100};
        }
    `else
        // On RV32, MINH/SINH/UINH/VSINH/VUINH live in mhpmevent*h[30:26]
        mhpmevent_inhibits_pattern_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH)[30:26]) {
                bins none_set  = {5'b00000};
                bins msu_set   = {5'b11100};
                bins minh_only = {5'b10000};
                bins sinh_only = {5'b01000};
                bins uinh_only = {5'b00100};
        }
    `endif

    `ifdef UDB_MXLEN_64
        mhpmevent_of: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT)[63] {}
        mhpmevent_of_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT)[63] {
                bins zero = {0};
        }
        mhpmevent_of_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT)[63] {
                bins one = {1};
        }
    `else
        // On RV32, Sscofpmf bits (including OF) live in mhpmevent*h[31:28]
        mhpmevent_of: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH)[31] {}
        mhpmevent_of_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH)[31] {
                bins zero = {0};
        }
        mhpmevent_of_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH)[31] {
                bins one = {1};
        }
    `endif
    `ifdef UDB_MXLEN_64
        mhpmevent_of_was_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSCOFPMF_MHPMEVENT)[63] {
                bins one = {1};
        }
        mhpmcounter_wraps: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSCOFPMF_MHPMCOUNTER) == `SSCOFPMF_COUNTER_MAX &
                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER,  `SSCOFPMF_MHPMCOUNTER) != `SSCOFPMF_COUNTER_MAX) {
                bins yes = {1};
        }
    `else
        mhpmevent_of_was_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSCOFPMF_MHPMEVENTH)[31] {
                bins one = {1};
        }
        mhpmcounter_wraps: coverpoint ({get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSCOFPMF_MHPMCOUNTERH), get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSCOFPMF_MHPMCOUNTER)} == `SSCOFPMF_COUNTER_MAX &
                                       {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER,  `SSCOFPMF_MHPMCOUNTERH), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER,  `SSCOFPMF_MHPMCOUNTER)} != `SSCOFPMF_COUNTER_MAX) {
                bins yes = {1};
        }
    `endif
    mip_clear: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MIP) == 0) {
            bins yes = {1};
    }
    mie_clear: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_MIE) == 0) {
            bins yes = {1};
    }

    mhpmcounter_extreme_state: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMCOUNTER)) {
            // On RV32 this is the low half of the counter
            bins all_ones  = {`UDB_MXLEN'(`SSCOFPMF_COUNTER_MAX)};
            bins all_zeros = {'0};
    }

    `ifdef UDB_MXLEN_64
        mhpmevent_all_zero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT) == '0) {
                bins yes = {1};
        }
    `else
        mhpmevent_all_zero: coverpoint ({get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENTH), get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, `SSCOFPMF_MHPMEVENT)} == '0) {
                bins yes = {1};
        }
    `endif
