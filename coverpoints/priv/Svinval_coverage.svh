///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVAL
covergroup Svinval_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include  "general/RISCV_coverage_standard_coverpoints.svh"

    cp_instr : coverpoint ins.current.insn {
        wildcard bins sfence_inval_ir = {SFENCE_INVAL_IR};
        wildcard bins sfence_w_inval  = {SFENCE_W_INVAL};
        wildcard bins sinval_vma      = {SINVAL_VMA};
        wildcard bins sfence_vma      = {SFENCE_VMA}; // not essential, but might as well cross it
    }
    cp_tvm : coverpoint ins.prev.csr[CSR_MSTATUS][20] {
        bins zero = {0};
    }
    cp_svinval : cross cp_instr, priv_mode_s_u, cp_tvm {
        // each instruction executed in S and U mode with TVM clear
    }
 endgroup

// ---------------------
function void svinval_sample(int hart, int issue, ins_t ins);

    Svinval_cg.sample(ins);
endfunction
