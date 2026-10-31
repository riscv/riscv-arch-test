///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   icount building blocks of the SdtrigSm/S/U icount covergroups. Each suite defines SDTRIG_ICOUNT_MODE_BIT,
//   the icount tdata1 bit of the mode its tests count in (m 9, s 7, u 6)
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
// csrr tdata1 of an armed icount trigger
icount_readback: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "type")[3:0] iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "type")[3:0] == 4'd3) {
    type_option.weight = 0;
    bins icount = {4'd3};
}
// the breakpoint taken on this record while an icount trigger is armed
icount_fired: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "type")[3:0] iff (sdtrig_bp_taken(ins)) {
    type_option.weight = 0;
    bins icount = {4'd3};
}
// armed count and pending, as written to tdata1 (before a readback, current on a fire record)
armed_gt1: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")) > 1,
                       get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")[8]} {
    type_option.weight = 0;
    bins count_gt1 = {2'b10};
}
armed_one: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")),
                       get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")[8]} {
    type_option.weight = 0;
    bins count_one = {15'b00000000000001_0};
}
armed_zero_mode: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")),
                             get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")[`SDTRIG_ICOUNT_MODE_BIT]} {
    type_option.weight = 0;
    bins count_zero_mode_set = {15'b00000000000000_1};
}
fired_gt1_mode: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")) > 1,
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")[`SDTRIG_ICOUNT_MODE_BIT]} {
    type_option.weight = 0;
    bins count_gt1_mode_set = {2'b11};
}
fired_one_mode: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")),
                            get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")[`SDTRIG_ICOUNT_MODE_BIT]} {
    type_option.weight = 0;
    bins count_one_mode_set = {15'b00000000000001_1};
}
fired_zero_pending: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")),
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")[8]} {
    type_option.weight = 0;
    bins count_zero_pending_set = {15'b00000000000000_1};
}
icount_count_result: coverpoint sdtrig_icount_outcome(ins, `SDTRIG_ICOUNT_MODE_BIT) {
    type_option.weight = 0;
    bins m_clear_not_counted = {3'd1};
    bins m_set_fired         = {3'd2};
}
icount_eq0_result: coverpoint sdtrig_icount_outcome(ins, `SDTRIG_ICOUNT_MODE_BIT) {
    type_option.weight = 0;
    bins pending_clear_no_fire = {3'd3};
    bins pending_set_fired     = {3'd4};
}
`ifdef UDB_SDTRIG_ICOUNT_COUNT_HARDWIRED_1
    // count hard-wired to 1, armed with m/s/u/vs/vu all set: firing clears all five and pending
    armed_hardwired: coverpoint {sdtrig_icount_count(get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")),
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")[26:25],
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")[9],
                                 get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "tdata1")[7:6]} {
        type_option.weight = 0;
        bins count_one_all_modes = {19'b00000000000001_11_1_11};
    }
    hardwired_result: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")[26:25],
                                  get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "tdata1")[9:6]} {
        type_option.weight = 0;
        bins modes_and_pending_cleared = {6'b00_0000};
    }
`endif
