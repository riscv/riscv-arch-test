///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu 29 November 2024
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSZAAMO
covergroup ExceptionsZaamo_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // building blocks for the main coverpoints
    amo_instrs: coverpoint ins.current.insn {
        wildcard bins amoswap_w = {AMOSWAP_W};
        wildcard bins amoadd_w  = {AMOADD_W};
        wildcard bins amoand_w  = {AMOAND_W};
        wildcard bins amoor_w   = {AMOOR_W};
        wildcard bins amoxor_w  = {AMOXOR_W};
        wildcard bins amomax_w  = {AMOMAX_W};
        wildcard bins amomaxu_w = {AMOMAXU_W};
        wildcard bins amomin_w  = {AMOMIN_W};
        wildcard bins amominu_w = {AMOMINU_W};
        `ifdef XLEN64
            wildcard bins amoswap_d = {AMOSWAP_D};
            wildcard bins amoadd_d  = {AMOADD_D};
            wildcard bins amoand_d  = {AMOAND_D};
            wildcard bins amoor_d   = {AMOOR_D};
            wildcard bins amoxor_d  = {AMOXOR_D};
            wildcard bins amomax_d  = {AMOMAX_D};
            wildcard bins amomaxu_d = {AMOMAXU_D};
            wildcard bins amomin_d  = {AMOMIN_D};
            wildcard bins amominu_d = {AMOMINU_D};
        `endif
        `ifdef ZABHA_SUPPORTED
            wildcard bins amoswap_h = {AMOSWAP_H};
            wildcard bins amoadd_h  = {AMOADD_H};
            wildcard bins amoand_h  = {AMOAND_H};
            wildcard bins amoor_h   = {AMOOR_H};
            wildcard bins amoxor_h  = {AMOXOR_H};
            wildcard bins amomax_h  = {AMOMAX_H};
            wildcard bins amomaxu_h = {AMOMAXU_H};
            wildcard bins amomin_h  = {AMOMIN_H};
            wildcard bins amominu_h = {AMOMINU_H};
            wildcard bins amoswap_b = {AMOSWAP_B};
            wildcard bins amoadd_b  = {AMOADD_B};
            wildcard bins amoand_b  = {AMOAND_B};
            wildcard bins amoor_b   = {AMOOR_B};
            wildcard bins amoxor_b  = {AMOXOR_B};
            wildcard bins amomax_b  = {AMOMAX_B};
            wildcard bins amomaxu_b = {AMOMAXU_B};
            wildcard bins amomin_b  = {AMOMIN_B};
            wildcard bins amominu_b = {AMOMINU_B};
        `endif
    }
    illegal_address: coverpoint ins.current.rs1_val {
        bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
    }
    // TODO: adjust number of lsbs based on MISALIGNED_MAX_ATOMICITY_GRANULE_SIZE
    adr_LSBs: coverpoint ins.current.rs1_val[4:0]  {
        // auto fills 00000 through 11111
    }
    // main coverpoints
    cp_amo_address_misaligned:  cross amo_instrs, adr_LSBs;
    cp_amo_access_fault:        cross amo_instrs, illegal_address;

endgroup

function void exceptionszaamo_sample(int hart, int issue, ins_t ins);
    ExceptionsZaamo_cg.sample(ins);
    // $display("rs1: %b, op[6:0]: %b, op:%b", ins.current.rs1_val[2:0], ins.current.insn[6:0], ins.current.insn);
endfunction
