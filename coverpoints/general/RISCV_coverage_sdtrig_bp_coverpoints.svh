///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Breakpoint building blocks of the SdtrigS/SdtrigU breakpoint covergroups: the trigger breakpoint taken from the
//   mode the tests run in.
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
// Triggers are armed in M through T-SBI; this covers the type of the trigger selected when a breakpoint is taken.
// itrigger/etrigger are left out: in these tests (medeleg[3] = 1) they are suppressed on harts that use the
// interrupt enables and fire into M on harts that use tcontrol, so neither outcome is a bin.
bp_type: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "tdata1", "type")[3:0] iff (sdtrig_bp_taken(ins)) {
    type_option.weight = 0;
    bins icount    = {4'd3};
    bins mcontrol6 = {4'd6};
}
// cp_breakpoint_delegate: medeleg[3] and the mode the breakpoint was handled in
bp_routing: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "medeleg")[3], ins.current.csr_wb[CSR_SCAUSE]} iff (sdtrig_bp_taken(ins)) {
    type_option.weight = 0;
    bins not_delegated_to_m = {2'b00};
    `ifdef UDB_MEDELEG_DELEGATABLE_3  // medeleg[3] is read-only 0 on a hart that uses tcontrol for reentrancy
        bins delegated_to_s = {2'b11};
    `endif
}
