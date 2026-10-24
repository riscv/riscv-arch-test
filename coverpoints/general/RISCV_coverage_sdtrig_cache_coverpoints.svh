///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Shared Coverpoints
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description:
//   Cache-operation building blocks of the SdtrigSm/S/U cache_operations covergroups
//   Weight 0: only the crosses count.
//
///////////////////////////////////////////
cbo_select: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata1", "select")[0] {
    type_option.weight = 0;
    bins address = {1'b0};
    bins data    = {1'b1};
}
// tdata2 relative to the cache block address in rs1
cbo_tdata2: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") {
    type_option.weight = 0;
    wildcard bins block      = {'x} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") == ins.current.rs1_val);
    wildcard bins below      = {'x} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") == ins.current.rs1_val - 1);
    wildcard bins next_block = {'x} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "tdata2", "tdata2") == ins.current.rs1_val + XLEN'(`UDB_CACHE_BLOCK_SIZE));
    bins zero                = {'0};
}
// fired (into M, mcause = 3) iff the operation matches as a store
cbo_outcome: coverpoint sdtrig_cbo_as_expected(ins) {
    type_option.weight = 0;
    bins as_expected = {1'b1};
}
`ifdef ZICBOM_SUPPORTED
    cbom_op: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins cbo_clean = {CBO_CLEAN};
        wildcard bins cbo_flush = {CBO_FLUSH};
        wildcard bins cbo_inval = {CBO_INVAL};
    }
`endif
`ifdef ZICBOZ_SUPPORTED
    cboz_op: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins cbo_zero = {CBO_ZERO};
    }
`endif
`ifdef ZICBOP_SUPPORTED
    prefetch_op: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins prefetch_i = {PREFETCH_I};
        wildcard bins prefetch_r = {PREFETCH_R};
        wildcard bins prefetch_w = {PREFETCH_W};
    }
`endif
