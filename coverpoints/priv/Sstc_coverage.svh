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
    mcounteren_tm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm")[0] {}
    mcounteren_tm_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm") {
        bins one = {1};
    }
    scounteren_tm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "tm")[0] {}
    scounteren_tm_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "tm") {
        bins one = {1};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0] {}
        menvcfg_stce_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce") {
            bins one = {1};
        }
    `else
        menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0] {}
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

// Sm tests are not part of a certificate without Sm (EXCLUDE_SM), so neither is their covergroup
`ifndef EXCLUDE_SM
covergroup Sstc_Sm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    mcounteren_tm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm")[0] {}
    mcounteren_tm_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm") {
        bins one = {1};
    }
    `ifdef UDB_MXLEN_64
        menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0] {}
        menvcfg_stce_one: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce") {
            bins one = {1};
        }
    `else
        menvcfg_stce: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0] {}
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
    cp_machine_tm:   cross priv_mode_m, csrr, stimecmp, mcounteren_tm, menvcfg_stce_one;
    cp_machine_stce: cross priv_mode_m, csrr, stimecmp, menvcfg_stce, mcounteren_tm_one;

    // also read stimecmph for RV32
    `ifdef UDB_MXLEN_32
        stimecmph: coverpoint ins.current.insn[31:20] {
            bins read_stimecmph = {CSR_STIMECMPH};
        }
        cp_machine_tm_h:   cross priv_mode_m, csrr, stimecmph, mcounteren_tm, menvcfg_stce_one;
        cp_machine_stce_h: cross priv_mode_m, csrr, stimecmph, menvcfg_stce, mcounteren_tm_one;
    `endif
endgroup
`endif

// H and HSm groups need the hypervisor extension.  stce_pair is {menvcfg.STCE, henvcfg.STCE} and tm_pair is
// {mcounteren.TM, hcounteren.TM} before the instruction; henvcfg.STCE is read-only zero while menvcfg.STCE = 0,
// so stce_pair has three reachable values.
`ifdef H_SUPPORTED
covergroup Sstc_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    `ifdef UDB_MXLEN_64
        stce_pair: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0],
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "stce")[0]} {
            bins m0_h0 = {2'b00};
            bins m1_h0 = {2'b10};
            bins m1_h1 = {2'b11};
        }
        stce_pair_ones: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "stce")[0]} {
            bins m1_h1 = {2'b11};
        }
        stce_pair_m1_h0: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0],
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "stce")[0]} {
            bins m1_h0 = {2'b10};
        }
    `else
        stce_pair: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0],
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "stce")[0]} {
            bins m0_h0 = {2'b00};
            bins m1_h0 = {2'b10};
            bins m1_h1 = {2'b11};
        }
        stce_pair_ones: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "stce")[0]} {
            bins m1_h1 = {2'b11};
        }
        stce_pair_m1_h0: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0],
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "stce")[0]} {
            bins m1_h0 = {2'b10};
        }
    `endif
    tm_pair: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm")[0],
                         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "tm")[0]} {
        bins m0_h0 = {2'b00};
        bins m0_h1 = {2'b01};
        bins m1_h0 = {2'b10};
        bins m1_h1 = {2'b11};
    }
    tm_pair_ones: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm")[0],
                              get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "tm")[0]} {
        bins m1_h1 = {2'b11};
    }
    tm_pair_m1_h0: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm")[0],
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "tm")[0]} {
        bins m1_h0 = {2'b10};
    }
    csrr: coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    stimecmp_csrs: coverpoint ins.current.insn[31:20] {
        bins stimecmp = {CSR_STIMECMP};
        `ifdef UDB_MXLEN_32
            bins stimecmph = {CSR_STIMECMPH};
        `endif
    }
    vstimecmp_csrs: coverpoint ins.current.insn[31:20] {
        bins vstimecmp = {CSR_VSTIMECMP};
        `ifdef UDB_MXLEN_32
            bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
    }
    timecmp_csrs: coverpoint ins.current.insn[31:20] {
        bins stimecmp  = {CSR_STIMECMP};
        bins vstimecmp = {CSR_VSTIMECMP};
        `ifdef UDB_MXLEN_32
            bins stimecmph  = {CSR_STIMECMPH};
            bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
    }
    // Accesses of csr_access_test: csrrw all 1s, csrrw 0s, csrrs all 1s, csrrc all 1s, csrr
    csraccesses: coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1);
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0);
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1);
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1);
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0);
    }

    hip: coverpoint ins.current.insn[31:20] {
        bins hip = {CSR_HIP};
    }
    hvip_vstip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vstip")[0] {
        // autofill 0/1
    }
    `ifdef UDB_MXLEN_64
        vstimecmp_val: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp") {
            bins zero = {64'h0};
            bins max  = {64'hFFFFFFFFFFFFFFFF};
        }
        vstimecmp_delta: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp") {
            bins zero    = {64'h0};
            bins p2_29   = {64'h0000000020000000};
            bins p2_31   = {64'h0000000080000000};
            bins p2_61   = {64'h2000000000000000};
            bins neg2_29 = {64'hFFFFFFFFE0000000};
            bins neg2_31 = {64'hFFFFFFFF80000000};
            bins neg2_61 = {64'hE000000000000000};
        }
        htimedelta_val: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta") {
            bins zero    = {64'h0};
            bins p2_30   = {64'h0000000040000000};
            bins p2_32m1 = {64'h00000000FFFFFFFF};
            bins p2_60   = {64'h1000000000000000};
            bins neg1    = {64'hFFFFFFFFFFFFFFFF};
            bins neg2_30 = {64'hFFFFFFFFC0000000};
            bins neg2_60 = {64'hF000000000000000};
        }
        htimedelta_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta") {
            bins zero = {64'h0};
        }
    `else
        vstimecmp_val: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmph", "vstimecmph"),
                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp")} {
            bins zero = {64'h0};
            bins max  = {64'hFFFFFFFFFFFFFFFF};
        }
        vstimecmp_delta: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmph", "vstimecmph"),
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp")} {
            bins zero    = {64'h0};
            bins p2_29   = {64'h0000000020000000};
            bins p2_31   = {64'h0000000080000000};
            bins p2_61   = {64'h2000000000000000};
            bins neg2_29 = {64'hFFFFFFFFE0000000};
            bins neg2_31 = {64'hFFFFFFFF80000000};
            bins neg2_61 = {64'hE000000000000000};
        }
        htimedelta_val: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedeltah", "htimedeltah"),
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta")} {
            bins zero    = {64'h0};
            bins p2_30   = {64'h0000000040000000};
            bins p2_32m1 = {64'h00000000FFFFFFFF};
            bins p2_60   = {64'h1000000000000000};
            bins neg1    = {64'hFFFFFFFFFFFFFFFF};
            bins neg2_30 = {64'hFFFFFFFFC0000000};
            bins neg2_60 = {64'hF000000000000000};
        }
        htimedelta_zero: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedeltah", "htimedeltah"),
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta")} {
            bins zero = {64'h0};
        }
    `endif

    // main coverpoints
    // HS-mode reaches vstimecmp only with menvcfg.STCE = mcounteren.TM = 1
    cp_hs_vstimecmp_accessible:   cross priv_mode_hs, csrr, vstimecmp_csrs, stce_pair, tm_pair;
    cp_hs_vstimecmp_accesses:     cross priv_mode_hs, csraccesses, vstimecmp_csrs, stce_pair_m1_h0, tm_pair_m1_h0;
    // stimecmp is vstimecmp in VS-mode, gated by both STCE and both TM bits; vstimecmp by its own name is never
    // accessible in VS-mode
    cp_vs_stimecmp_accessible:    cross priv_mode_vs, csrr, stimecmp_csrs, stce_pair, tm_pair;
    cp_vs_vstimecmp_inaccessible: cross priv_mode_vs, csrr, vstimecmp_csrs, stce_pair, tm_pair;
    cp_vs_stimecmp_accesses:      cross priv_mode_vs, csraccesses, stimecmp_csrs, stce_pair_ones, tm_pair_ones;
    // Illegal instruction when HS-mode could not access them, else virtual instruction in VU-mode; always illegal
    // instruction in U-mode
    cp_vu_timecmp_inaccessible:   cross priv_mode_vu, csrr, timecmp_csrs, stce_pair, tm_pair;
    cp_u_timecmp_inaccessible:    cross priv_mode_u, csrr, timecmp_csrs, stce_pair, tm_pair;
    // hip.VSTIP is hvip.VSTIP | (menvcfg.STCE & henvcfg.STCE & time + htimedelta >= vstimecmp), unsigned
    cp_vstip:                     cross priv_mode_hs, csrr, hip, stce_pair, hvip_vstip, vstimecmp_val, htimedelta_zero;
    cp_htimedelta:                cross priv_mode_hs, csrr, hip, stce_pair_ones, htimedelta_val, vstimecmp_delta;
endgroup

// Sm tests are not part of a certificate without Sm (EXCLUDE_SM), so neither is their covergroup
`ifndef EXCLUDE_SM
covergroup Sstc_HSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // building blocks for the main coverpoints
    `ifdef UDB_MXLEN_64
        stce_pair: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0],
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "stce")[0]} {
            bins m0_h0 = {2'b00};
            bins m1_h0 = {2'b10};
            bins m1_h1 = {2'b11};
        }
        stce_pair_ones: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "stce")[0]} {
            bins m1_h1 = {2'b11};
        }
        stce_pair_m1_h0: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "stce")[0],
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfg", "stce")[0]} {
            bins m1_h0 = {2'b10};
        }
    `else
        stce_pair: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0],
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "stce")[0]} {
            bins m0_h0 = {2'b00};
            bins m1_h0 = {2'b10};
            bins m1_h1 = {2'b11};
        }
        stce_pair_ones: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0],
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "stce")[0]} {
            bins m1_h1 = {2'b11};
        }
        stce_pair_m1_h0: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfgh", "stce")[0],
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "henvcfgh", "stce")[0]} {
            bins m1_h0 = {2'b10};
        }
    `endif
    tm_pair: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm")[0],
                         get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "tm")[0]} {
        bins m0_h0 = {2'b00};
        bins m0_h1 = {2'b01};
        bins m1_h0 = {2'b10};
        bins m1_h1 = {2'b11};
    }
    tm_pair_zeros: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "tm")[0],
                               get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "tm")[0]} {
        bins m0_h0 = {2'b00};
    }
    csrr: coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    vstimecmp_csrs: coverpoint ins.current.insn[31:20] {
        bins vstimecmp = {CSR_VSTIMECMP};
        `ifdef UDB_MXLEN_32
            bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
    }
    // Accesses of csr_access_test: csrrw all 1s, csrrw 0s, csrrs all 1s, csrrc all 1s, csrr
    csraccesses: coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1);
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0);
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1);
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1);
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0);
    }
    hip: coverpoint ins.current.insn[31:20] {
        bins hip = {CSR_HIP};
    }
    hvip_vstip: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hvip", "vstip")[0] {
        // autofill 0/1
    }
    `ifdef UDB_MXLEN_64
        vstimecmp_val: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp") {
            bins zero = {64'h0};
            bins max  = {64'hFFFFFFFFFFFFFFFF};
        }
        vstimecmp_delta: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp") {
            bins zero    = {64'h0};
            bins p2_29   = {64'h0000000020000000};
            bins p2_31   = {64'h0000000080000000};
            bins p2_61   = {64'h2000000000000000};
            bins neg2_29 = {64'hFFFFFFFFE0000000};
            bins neg2_31 = {64'hFFFFFFFF80000000};
            bins neg2_61 = {64'hE000000000000000};
        }
        htimedelta_val: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta") {
            bins zero    = {64'h0};
            bins p2_30   = {64'h0000000040000000};
            bins p2_32m1 = {64'h00000000FFFFFFFF};
            bins p2_60   = {64'h1000000000000000};
            bins neg1    = {64'hFFFFFFFFFFFFFFFF};
            bins neg2_30 = {64'hFFFFFFFFC0000000};
            bins neg2_60 = {64'hF000000000000000};
        }
        htimedelta_zero: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta") {
            bins zero = {64'h0};
        }
    `else
        vstimecmp_val: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmph", "vstimecmph"),
                                   get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp")} {
            bins zero = {64'h0};
            bins max  = {64'hFFFFFFFFFFFFFFFF};
        }
        vstimecmp_delta: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmph", "vstimecmph"),
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstimecmp", "vstimecmp")} {
            bins zero    = {64'h0};
            bins p2_29   = {64'h0000000020000000};
            bins p2_31   = {64'h0000000080000000};
            bins p2_61   = {64'h2000000000000000};
            bins neg2_29 = {64'hFFFFFFFFE0000000};
            bins neg2_31 = {64'hFFFFFFFF80000000};
            bins neg2_61 = {64'hE000000000000000};
        }
        htimedelta_val: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedeltah", "htimedeltah"),
                                    get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta")} {
            bins zero    = {64'h0};
            bins p2_30   = {64'h0000000040000000};
            bins p2_32m1 = {64'h00000000FFFFFFFF};
            bins p2_60   = {64'h1000000000000000};
            bins neg1    = {64'hFFFFFFFFFFFFFFFF};
            bins neg2_30 = {64'hFFFFFFFFC0000000};
            bins neg2_60 = {64'hF000000000000000};
        }
        htimedelta_zero: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedeltah", "htimedeltah"),
                                     get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htimedelta", "htimedelta")} {
            bins zero = {64'h0};
        }
    `endif

    // main coverpoints
    // hip.VSTIP is hvip.VSTIP | (menvcfg.STCE & henvcfg.STCE & time + htimedelta >= vstimecmp), unsigned
    cp_vstip:                  cross priv_mode_m, csrr, hip, stce_pair, hvip_vstip, vstimecmp_val, htimedelta_zero;
    cp_htimedelta:             cross priv_mode_m, csrr, hip, stce_pair_ones, htimedelta_val, vstimecmp_delta;
    // M-mode reaches vstimecmp whatever the enables hold
    cp_m_vstimecmp_accessible: cross priv_mode_m, csrr, vstimecmp_csrs, stce_pair, tm_pair;
    cp_m_vstimecmp_accesses:   cross priv_mode_m, csraccesses, vstimecmp_csrs, stce_pair_m1_h0, tm_pair_zeros;
endgroup
`endif
`endif

function void sstc_sample(int hart, int issue, ins_t ins);
    Sstc_cg.sample(ins);
    `ifndef EXCLUDE_SM
        Sstc_Sm_cg.sample(ins);
    `endif
    `ifdef H_SUPPORTED
        Sstc_H_cg.sample(ins);
        `ifndef EXCLUDE_SM
            Sstc_HSm_cg.sample(ins);
        `endif
    `endif
endfunction
