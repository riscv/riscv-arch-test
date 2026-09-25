///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Written: Umer Shahid umer@riscv.org September 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVALSM
covergroup SvinvalSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    cp_instr : coverpoint ins.current.insn {
        wildcard bins sfence_inval_ir = {SFENCE_INVAL_IR};
        wildcard bins sfence_w_inval  = {SFENCE_W_INVAL};
        wildcard bins sinval_vma      = {SINVAL_VMA};
        wildcard bins sfence_vma      = {SFENCE_VMA}; // not essential, but might as well cross it
    }
    cp_tvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm")[0] {
        bins zero = {0};
        bins set  = {1};
    }
    cr_svinival : cross cp_instr, priv_mode_m_s_u, cp_tvm {
        // each instruction executed in every mode with mstatus.TVM clear and set
    }
 endgroup

// ---------------------
function void svinvalsm_sample(int hart, int issue, ins_t ins);

    SvinvalSm_cg.sample(ins);
endfunction
