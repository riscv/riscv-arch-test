///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SVINVALSM
covergroup SvinvalSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    cp_instr : coverpoint ins.current.insn {
        wildcard bins sfence_inval_ir = {SFENCE_INVAL_IR};
        wildcard bins sfence_w_inval  = {SFENCE_W_INVAL};
        wildcard bins sinval_vma      = {SINVAL_VMA};
        wildcard bins sfence_vma      = {SFENCE_VMA}; // not essential, but might as well cross it
    }
    cp_priv : coverpoint {ins.prev.mode} {
        bins M_mode     = {2'b11};
        bins S_mode     = {2'b01};
        bins U_mode     = {2'b00};
    }
    cp_tvm : coverpoint ins.prev.csr[CSR_MSTATUS][20] {
        bins zero = {0};
        bins set  = {1};
    }
    cr_svinival : cross cp_instr, cp_priv, cp_tvm {
        // each instruction executed in M mode with each TVM, and in S and U mode with TVM set
        ignore_bins lower_tvm_zero = (binsof(cp_priv.S_mode) || binsof(cp_priv.U_mode)) && binsof(cp_tvm.zero);
    }
 endgroup

// ---------------------
function void svinvalsm_sample(int hart, int issue, ins_t ins);

    SvinvalSm_cg.sample(ins);
endfunction
