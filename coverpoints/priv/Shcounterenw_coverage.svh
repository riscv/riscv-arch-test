///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Shcounterenw: hcounteren bits are writable for implemented hpmcounters.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SHCOUNTERENW
covergroup Shcounterenw_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    hcounteren: coverpoint ins.current.insn[31:20] {
        bins hcounteren = {CSR_HCOUNTEREN};
    }
    hcounteren_write: coverpoint ins.current.rs1_val[31:0] {
        bins zeros = {32'h0};
        bins ones  = {32'hFFFFFFFF};
    }

    cp_shcounterenw: cross priv_mode_hs, csrrw, hcounteren, hcounteren_write;
endgroup

`ifndef EXCLUDE_SM
covergroup Shcounterenw_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // n is the shift amount of the srli that isolates hcounteren bit n after HS-mode writes all ones to hcounteren.
    // A bin counts only when the bit reads 1 and M-mode found mhpmcounter<n> implemented: the test sets it to all
    // ones before the check and clears it after.
    hcounteren_bit_n: coverpoint ins.current.insn[24:20] iff (
        ins.current.insn ==? SRLI &&
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, CSR_HCOUNTEREN)[ins.current.insn[24:20]] == 1'b1 &&
        (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, 12'(CSR_MHPMCOUNTER3 + ins.current.insn[24:20] - 5'd3)) != '0
        `ifdef UDB_MXLEN_32
            || get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, 12'(CSR_MHPMCOUNTER3H + ins.current.insn[24:20] - 5'd3)) != '0
        `endif
        )) {
        bins n[] = {[3:31]};
    }

    cp_hpmcounter_hcounteren: cross priv_mode_hs, hcounteren_bit_n;
endgroup
`endif // EXCLUDE_SM

function void shcounterenw_sample(int hart, int issue, ins_t ins);
    Shcounterenw_cg.sample(ins);
`ifndef EXCLUDE_SM
    Shcounterenw_Sm_cg.sample(ins);
`endif // EXCLUDE_SM
endfunction
