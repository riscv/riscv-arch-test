///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SSCOUNTERENWSM
covergroup SscounterenwSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // n is the slli amount on the and that isolates one scounteren bit.
    // The bin hits only when that bit is 1 and hpmcounter<n> is not zero.
    // On RV32 the high half counts. A read-only-zero counter branches past this and.
    `ifdef ZIHPM_SUPPORTED
    cp_hpmcounter_scounteren: coverpoint ins.prev.insn[24:20] {
        bins n[] = {[5'd3:5'd31]} iff (
            ins.trap == 0 &&
            {ins.prev.mode_virt, ins.prev.mode} == 3'b001 &&
            (ins.prev.insn ==? SLLI) &&
            (ins.current.insn ==? AND) &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, CSR_SCOUNTEREN)[int'(ins.prev.insn[24:20])] == 1'b1 &&
            (
                get_csr_val(
                    ins.hart, ins.issue, `SAMPLE_AFTER,
                    12'(CSR_MHPMCOUNTER3 + ins.prev.insn[24:20] - 5'd3)
                ) != '0
                `ifdef UDB_MXLEN_32
                || get_csr_val(
                    ins.hart, ins.issue, `SAMPLE_AFTER,
                    12'(CSR_MHPMCOUNTER3H + ins.prev.insn[24:20] - 5'd3)
                ) != '0
                `endif
            )
        );
    }
    `endif

endgroup

function void sscounterenwsm_sample(int hart, int issue, ins_t ins);
    SscounterenwSm_cg.sample(ins);
endfunction
