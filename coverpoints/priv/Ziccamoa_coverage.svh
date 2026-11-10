///////////////////////////////////////////////
// RISC-V Architectural Functional Coverage Covergroups
//
// Written:  David_Harris@hmc.edu 22 October 2026
//
// Copyright (C) 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for Ziccamoa extension (main memory supports all atomics in A)
///////////////////////////////////////////////


`define COVER_ZICCAMOA

covergroup Ziccamoa_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    cp_ziccamoa: coverpoint ins.current.insn {
        wildcard bins amoswap_w = {AMOSWAP_W};
        wildcard bins amoadd_w = {AMOADD_W};
        wildcard bins amoand_w = {AMOAND_W};
        wildcard bins amoor_w = {AMOOR_W};
        wildcard bins amoxor_w = {AMOXOR_W};
        wildcard bins amomin_w = {AMOMIN_W};
        wildcard bins amomax_w = {AMOMAX_W};
        wildcard bins amominu_w = {AMOMINU_W};
        wildcard bins amomaxu_w = {AMOMAXU_W};
        `ifdef UDB_MXLEN_64
            wildcard bins amoswap_d = {AMOSWAP_D};
            wildcard bins amoadd_d = {AMOADD_D};
            wildcard bins amoand_d = {AMOAND_D};
            wildcard bins amoor_d = {AMOOR_D};
            wildcard bins amoxor_d = {AMOXOR_D};
            wildcard bins amomin_d = {AMOMIN_D};
            wildcard bins amomax_d = {AMOMAX_D};
            wildcard bins amominu_d = {AMOMINU_D};
            wildcard bins amomaxu_d = {AMOMAXU_D};
        `endif
        `ifdef ZABHA_SUPPORTED
            wildcard bins amoswap_b = {AMOSWAP_B};
            wildcard bins amoadd_b = {AMOADD_B};
            wildcard bins amoand_b = {AMOAND_B};
            wildcard bins amoor_b = {AMOOR_B};
            wildcard bins amoxor_b = {AMOXOR_B};
            wildcard bins amomin_b = {AMOMIN_B};
            wildcard bins amomax_b = {AMOMAX_B};
            wildcard bins amominu_b = {AMOMINU_B};
            wildcard bins amomaxu_b = {AMOMAXU_B};
            wildcard bins amoswap_h = {AMOSWAP_H};
            wildcard bins amoadd_h = {AMOADD_H};
            wildcard bins amoand_h = {AMOAND_H};
            wildcard bins amoor_h = {AMOOR_H};
            wildcard bins amoxor_h = {AMOXOR_H};
            wildcard bins amomin_h = {AMOMIN_H};
            wildcard bins amomax_h = {AMOMAX_H};
            wildcard bins amominu_h = {AMOMINU_H};
            wildcard bins amomaxu_h = {AMOMAXU_H};
        `endif
    }

endgroup

function void ziccamoa_sample(int hart, int issue, ins_t ins);
    Ziccamoa_cg.sample(ins);
endfunction
