///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Written: Angela Zheng, angela20061015@gmail.com, 10 September 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Debug Trigger coverpoints common to SdtrigSm, SdtrigS, SdtrigU
//
///////////////////////////////////////////
`ifndef
    `define UDB_NUM_TRIGGERS 2
`endif

triggernum: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tselect", "tselect") {
    type_option.weight = 0;
    bins all_triggers[] = {[0:`UDB_NUM_TRIGGERS-1]};
}
