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
    cp_tvm : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm")[0] {
        bins zero = {0};
    }
    cp_svinval : cross cp_instr, priv_mode_s_u, cp_tvm {
        // each instruction executed in S and U mode with TVM clear
    }

    // The SFENCE.W.INVAL, SINVAL.VMA, SFENCE.INVAL.IR sequence in S-mode after a leaf change, with x0 or a register
    // in rs1 and rs2.  The test checks that the next access uses the new leaf.
    sinval_vma : coverpoint ins.current.insn {
        wildcard bins sinval_vma = {SINVAL_VMA};
    }
    rs1 : coverpoint ins.get_gpr_reg(ins.current.rs1) iff (ins.ins_str inside {"sinval.vma"}) {
        bins x0       = {x0};
        bins register = {[x1:x31]};
    }
    rs2 : coverpoint ins.get_gpr_reg(ins.current.rs2) iff (ins.ins_str inside {"sinval.vma"}) {
        bins x0       = {x0};
        bins register = {[x1:x31]};
    }
    satp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
        bins paged = {[1:15]};
    }
    cp_sinval_vma : cross priv_mode_s, sinval_vma, satp_paged, rs1, rs2;
endgroup

// Sm tests are not part of a certificate without Sm (EXCLUDE_SM), so neither is their covergroup
`ifndef EXCLUDE_SM
covergroup Svinval_Sm_cg with function sample(ins_t ins);
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
    cp_svinval : cross cp_instr, priv_mode_m_s_u, cp_tvm {
        // each instruction executed in every mode with mstatus.TVM clear and set
    }
 endgroup
`endif

// H tests need the hypervisor extension, so their covergroups are only in a configuration with H
`ifdef H_SUPPORTED
// H_TWO_STAGE: two-stage translation, for the invalidation tests
`include "general/RISCV_coverage_hypervisor.svh"

// Svinval instructions in HS, VS, U and VU modes with mstatus.TVM = 0 and hstatus.VTVM = 0, 1, and
// invalidation of changed VS-stage and G-stage leaves.
// Written: Julia Gong jgong@g.hmc.edu November 10, 2025
covergroup Svinval_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    svinval: coverpoint ins.current.insn {
        wildcard bins sfence_w_inval  = {SFENCE_W_INVAL};
        wildcard bins sinval_vma      = {SINVAL_VMA};
        wildcard bins sfence_inval_ir = {SFENCE_INVAL_IR};
        wildcard bins hinval_vvma     = {HINVAL_VVMA};
        wildcard bins hinval_gvma     = {HINVAL_GVMA};
    }
    mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins off = {0};
    }
    hstatus_vtvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins off = {0};
        bins on  = {1};
    }

    // mstatus.TVM = 1 and M-mode are in Svinval_SmH_cg
    cp_svinval: cross priv_mode_hs_vs_u_vu, svinval, mstatus_tvm, hstatus_vtvm;

    // The SFENCE.W.INVAL, HINVAL.VVMA or HINVAL.GVMA (or SINVAL.VMA in VS-mode), SFENCE.INVAL.IR sequence after a
    // VS-stage or G-stage leaf change, with x0 or a register in rs1 and rs2.  The test checks that the next guest
    // access uses the new leaf.
    `ifdef H_TWO_STAGE
        hinval_vvma : coverpoint ins.current.insn {
            wildcard bins hinval_vvma = {HINVAL_VVMA};
        }
        hinval_gvma : coverpoint ins.current.insn {
            wildcard bins hinval_gvma = {HINVAL_GVMA};
        }
        sinval_vma : coverpoint ins.current.insn {
            wildcard bins sinval_vma = {SINVAL_VMA};
        }
        rs1 : coverpoint ins.get_gpr_reg(ins.current.rs1) iff (ins.ins_str inside {"sinval.vma", "hinval.vvma", "hinval.gvma"}) {
            bins x0       = {x0};
            bins register = {[x1:x31]};
        }
        rs2 : coverpoint ins.get_gpr_reg(ins.current.rs2) iff (ins.ins_str inside {"sinval.vma", "hinval.vvma", "hinval.gvma"}) {
            bins x0       = {x0};
            bins register = {[x1:x31]};
        }
        vsatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsatp", "mode") {
            bins paged = {[1:15]};
        }
        hgatp_paged : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hgatp", "mode") {
            bins paged = {[1:15]};
        }

        cp_hinval_vvma   : cross priv_mode_hs, hinval_vvma, vsatp_paged, hgatp_paged, rs1, rs2;
        cp_hinval_gvma   : cross priv_mode_hs, hinval_gvma, vsatp_paged, hgatp_paged, rs1, rs2;
        cp_sinval_vma_vs : cross priv_mode_vs, sinval_vma, vsatp_paged, hgatp_paged, rs1, rs2;
    `endif
endgroup

`ifndef EXCLUDE_SM
// Svinval instructions in M-mode with mstatus.TVM = 0, 1, and in HS, VS, U and VU modes with
// mstatus.TVM = 1, each with hstatus.VTVM = 0, 1.
// Written: David_Harris@hmc.edu 24 September 2026
covergroup Svinval_SmH_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    svinval: coverpoint ins.current.insn {
        wildcard bins sfence_w_inval  = {SFENCE_W_INVAL};
        wildcard bins sinval_vma      = {SINVAL_VMA};
        wildcard bins sfence_inval_ir = {SFENCE_INVAL_IR};
        wildcard bins hinval_vvma     = {HINVAL_VVMA};
        wildcard bins hinval_gvma     = {HINVAL_GVMA};
    }
    mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins off = {0};
        bins on  = {1};
    }
    mstatus_tvm_on: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins on = {1};
    }
    hstatus_vtvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins off = {0};
        bins on  = {1};
    }

    // Svinval_H_cg covers the lower modes with mstatus.TVM = 0
    cp_svinval_m:   cross priv_mode_m, svinval, mstatus_tvm, hstatus_vtvm;
    cp_svinval_tvm: cross priv_mode_hs_vs_u_vu, svinval, mstatus_tvm_on, hstatus_vtvm;
endgroup
`endif
`endif

// ---------------------
function void svinval_sample(int hart, int issue, ins_t ins);

    Svinval_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Svinval_Sm_cg.sample(ins);
    `endif
    `ifdef H_SUPPORTED
        Svinval_H_cg.sample(ins);
        `ifndef EXCLUDE_SM
            Svinval_SmH_cg.sample(ins);
        `endif
    `endif
endfunction
