///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Corey Hickson chickson@hmc.edu, Sadhvi Narayanan sanarayanan@hmc.edu April 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////


`define COVER_SSTCS


covergroup SstcS_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"


    // building blocks for the main coverpoints

    mcounteren_tm: coverpoint ins.current.csr[CSR_MCOUNTEREN][1];
    scounteren_tm: coverpoint ins.current.csr[CSR_SCOUNTEREN][1];
    `ifdef UDB_MXLEN_64
        menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFG][63];
    `else
        menvcfg_stce: coverpoint ins.current.csr[CSR_MENVCFGH][31];
    `endif
    csrr: coverpoint ins.current.insn[6:0] {
        bins csrr = {7'b1110011};
    }
    read_stimecmp: coverpoint ins.current.insn[31:20] {
        bins read_stimecmp = {CSR_STIMECMP};
    }

    // main coverpoints
    cp_supervisor_tm:   cross priv_mode_s, csrr, read_stimecmp, mcounteren_tm;
    cp_supervisor_stce: cross priv_mode_s, csrr, read_stimecmp, menvcfg_stce;

    cp_user_tm:     cross priv_mode_u, csrr, read_stimecmp, mcounteren_tm, scounteren_tm;
    cp_user_stce:       cross priv_mode_u, csrr, read_stimecmp, menvcfg_stce;

    // also read STIMECMPH for RV32
    `ifdef UDB_MXLEN_32
        read_stimecmph: coverpoint ins.current.insn[31:20] {
            bins read_stimecmp = {CSR_STIMECMPH};
        }
        cp_supervisor_tm_h:   cross priv_mode_s, csrr, read_stimecmph, mcounteren_tm;
        cp_supervisor_stce_h: cross priv_mode_s, csrr, read_stimecmph, menvcfg_stce;

        cp_user_tm_h:     cross priv_mode_u, csrr, read_stimecmph, mcounteren_tm, scounteren_tm;
        cp_user_stce_h:       cross priv_mode_u, csrr, read_stimecmph, menvcfg_stce;

    `endif

endgroup


function void sstcs_sample(int hart, int issue, ins_t ins);
    SstcS_cg.sample(ins);
endfunction
