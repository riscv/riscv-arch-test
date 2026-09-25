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

`define COVER_SSTC

covergroup Sstc_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    mcounteren_tm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm") {
        bins zero = {0};
        bins one  = {1};
    }
    mcounteren_tm_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm") {
        bins one = {1};
    }
    scounteren_tm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "tm") {
        bins zero = {0};
        bins one  = {1};
    }
    scounteren_tm_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "tm") {
        bins one = {1};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce") {
            bins zero = {0};
            bins one  = {1};
        }
        menvcfg_stce_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce") {
            bins one = {1};
        }
    `else
        menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce") {
            bins zero = {0};
            bins one  = {1};
        }
        menvcfg_stce_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce") {
            bins one = {1};
        }
    `endif
    csrr: coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    stimecmp: coverpoint ins.current.insn[31:20] {
        bins read_stimecmp = {CSR_STIMECMP};
    }

    // main coverpoints: each crosses one of mcounteren.TM and menvcfg.STCE with the other held at 1
    cp_supervisor_tm:   cross priv_mode_s, csrr, stimecmp, mcounteren_tm, menvcfg_stce_one;
    cp_supervisor_stce: cross priv_mode_s, csrr, stimecmp, menvcfg_stce, mcounteren_tm_one;
    cp_user_tm:         cross priv_mode_u, csrr, stimecmp, mcounteren_tm, scounteren_tm, menvcfg_stce_one;
    cp_user_stce:       cross priv_mode_u, csrr, stimecmp, menvcfg_stce, mcounteren_tm_one, scounteren_tm_one;

    // also read stimecmph for RV32
    `ifdef UDB_MXLEN_32
        stimecmph: coverpoint ins.current.insn[31:20] {
            bins read_stimecmph = {CSR_STIMECMPH};
        }
        cp_supervisor_tm_h:   cross priv_mode_s, csrr, stimecmph, mcounteren_tm, menvcfg_stce_one;
        cp_supervisor_stce_h: cross priv_mode_s, csrr, stimecmph, menvcfg_stce, mcounteren_tm_one;
        cp_user_tm_h:         cross priv_mode_u, csrr, stimecmph, mcounteren_tm, scounteren_tm, menvcfg_stce_one;
        cp_user_stce_h:       cross priv_mode_u, csrr, stimecmph, menvcfg_stce, mcounteren_tm_one, scounteren_tm_one;
    `endif
endgroup

function void sstc_sample(int hart, int issue, ins_t ins);
    Sstc_cg.sample(ins);
endfunction
