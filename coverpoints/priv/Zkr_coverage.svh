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

    seed_csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw_seed = {32'b000000010101_?????_001_?????_1110011};
    }

    csrops_seed_illegal: coverpoint ins.current.insn {
        wildcard bins csrrs_seed  = {32'b000000010101_?????_010_?????_1110011};
        wildcard bins csrrc_seed  = {32'b000000010101_?????_011_?????_1110011};
        wildcard bins csrrwi_seed = {32'b000000010101_?????_101_?????_1110011};
        wildcard bins csrrsi_seed = {32'b000000010101_?????_110_?????_1110011};
        wildcard bins csrrci_seed = {32'b000000010101_?????_111_?????_1110011};
        wildcard bins csrw_seed  = {32'b000000010101_?????_001_00000_1110011};
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
    cp_zkr_seed_csrrw_M: cross seed_csrrw, priv_mode_m, mseccfg_sseed, mseccfg_useed;
    cp_zkr_seed_illegal_csr_op_M: cross csrops_seed_illegal, rs1_imm_0_1, priv_mode_m;
`ifdef S_SUPPORTED
    cp_zkr_seed_csrrw_S: cross seed_csrrw, priv_mode_s, mseccfg_sseed, mseccfg_useed;
    cp_zkr_seed_illegal_csr_op_S: cross csrops_seed_illegal, rs1_imm_0_1, priv_mode_s;
`endif
`ifdef U_SUPPORTED
    cp_zkr_seed_csrrw_U: cross seed_csrrw, priv_mode_u, mseccfg_sseed, mseccfg_useed;
    cp_zkr_seed_illegal_csr_op_U: cross csrops_seed_illegal, rs1_imm_0_1, priv_mode_u;
`endif

endgroup

function void zkr_sample(int hart, int issue, ins_t ins);
    Zkr_cg.sample(ins);
endfunction
