///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Julia Gong jgong@g.hmc.edu April 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZKR
covergroup Zkr_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }

    csrops_illegal: coverpoint ins.current.insn {
        wildcard bins csrrs  = {CSRRS};
        wildcard bins csrrc  = {CSRRC};
        wildcard bins csrrwi = {CSRRWI};
        wildcard bins csrrsi = {CSRRSI};
        wildcard bins csrrci = {CSRRCI};
    }

    seed_csr: coverpoint ins.current.insn[31:20] {
        bins seed = {CSR_SEED};
    }

    rs1_imm_0_1: coverpoint ins.current.insn[19:15] {
        bins zero    = {5'b00000};
        bins nonzero = {[5'b00001:5'b11111]};
    }

    mseccfg_sseed: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "sseed")[0] {
        bins set   = {1};
        bins clear = {0};
    }
    mseccfg_useed: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mseccfg", "useed")[0] {
        bins set   = {1};
        bins clear = {0};
    }

    // Main coverpoints
    cp_zkr_seed_csrrw_M: cross csrrw, seed_csr, rs1_imm_0_1, priv_mode_m, mseccfg_sseed, mseccfg_useed;
    cp_zkr_seed_illegal_csr_op_M: cross csrops_illegal, seed_csr, rs1_imm_0_1, priv_mode_m;
`ifdef S_SUPPORTED
    cp_zkr_seed_csrrw_S: cross csrrw, seed_csr, rs1_imm_0_1, priv_mode_s, mseccfg_sseed, mseccfg_useed;
    cp_zkr_seed_illegal_csr_op_S: cross csrops_illegal, seed_csr, rs1_imm_0_1, priv_mode_s;
`endif
`ifdef U_SUPPORTED
    cp_zkr_seed_csrrw_U: cross csrrw, seed_csr, rs1_imm_0_1, priv_mode_u, mseccfg_sseed, mseccfg_useed;
    cp_zkr_seed_illegal_csr_op_U: cross csrops_illegal, seed_csr, rs1_imm_0_1, priv_mode_u;
`endif

endgroup

function void zkr_sample(int hart, int issue, ins_t ins);
    Zkr_cg.sample(ins);
endfunction
