///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Sstc hypervisor tests executed in M-mode: vstimecmp, htimedelta and hip.VSTIP.
// Written: David_Harris@hmc.edu 25 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSTCHSM

covergroup SstcHSm_m_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrr : coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    // Accesses of csr_access_test: csrrw all 1s, csrrw 0s, csrrs all 1s, csrrc all 1s, csrr
    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1);
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0);
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1);
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1);
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0);
    }
    hip : coverpoint ins.current.insn[31:20] {
        bins hip = {CSR_HIP};
    }
    vstimecmp : coverpoint ins.current.insn[31:20] {
        bins vstimecmp = {CSR_VSTIMECMP};
        `ifdef UDB_MXLEN_32
            bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
    }
    vstimecmp_low : coverpoint ins.current.insn[31:20] {
        bins vstimecmp = {CSR_VSTIMECMP};
    }

    // menvcfg.STCE, henvcfg.STCE, mcounteren.TM, hcounteren.TM, vstimecmp and htimedelta before the instruction
    `ifdef UDB_MXLEN_64
        `define SSTCHSM_MSTCE ins.prev.csr[CSR_MENVCFG][63]
        `define SSTCHSM_HSTCE ins.prev.csr[CSR_HENVCFG][63]
        vstimecmp_val : coverpoint ins.prev.csr[CSR_VSTIMECMP] {
            bins zero = {64'h0};
            bins max  = {64'hFFFFFFFFFFFFFFFF};
        }
        vstimecmp_delta : coverpoint ins.prev.csr[CSR_VSTIMECMP] {
            bins zero      = {64'h0};
            bins p2_29     = {64'h0000000020000000};
            bins p2_31     = {64'h0000000080000000};
            bins p2_61     = {64'h2000000000000000};
            bins neg2_29   = {64'hFFFFFFFFE0000000};
            bins neg2_31   = {64'hFFFFFFFF80000000};
            bins neg2_61   = {64'hE000000000000000};
        }
        htimedelta_val : coverpoint ins.prev.csr[CSR_HTIMEDELTA] {
            bins zero    = {64'h0};
            bins p2_30   = {64'h0000000040000000};
            bins p2_60   = {64'h1000000000000000};
            bins neg2_30 = {64'hFFFFFFFFC0000000};
            bins neg2_60 = {64'hF000000000000000};
        }
        htimedelta_zero : coverpoint ins.prev.csr[CSR_HTIMEDELTA] {
            bins zero = {64'h0};
        }
    `else
        `define SSTCHSM_MSTCE ins.prev.csr[CSR_MENVCFGH][31]
        `define SSTCHSM_HSTCE ins.prev.csr[CSR_HENVCFGH][31]
        vstimecmp_val : coverpoint {ins.prev.csr[CSR_VSTIMECMPH], ins.prev.csr[CSR_VSTIMECMP]} {
            bins zero = {64'h0};
            bins max  = {64'hFFFFFFFFFFFFFFFF};
        }
        vstimecmp_delta : coverpoint {ins.prev.csr[CSR_VSTIMECMPH], ins.prev.csr[CSR_VSTIMECMP]} {
            bins zero      = {64'h0};
            bins p2_29     = {64'h0000000020000000};
            bins p2_31     = {64'h0000000080000000};
            bins p2_61     = {64'h2000000000000000};
            bins neg2_29   = {64'hFFFFFFFFE0000000};
            bins neg2_31   = {64'hFFFFFFFF80000000};
            bins neg2_61   = {64'hE000000000000000};
        }
        htimedelta_val : coverpoint {ins.prev.csr[CSR_HTIMEDELTAH], ins.prev.csr[CSR_HTIMEDELTA]} {
            bins zero    = {64'h0};
            bins p2_30   = {64'h0000000040000000};
            bins p2_60   = {64'h1000000000000000};
            bins neg2_30 = {64'hFFFFFFFFC0000000};
            bins neg2_60 = {64'hF000000000000000};
        }
        htimedelta_zero : coverpoint {ins.prev.csr[CSR_HTIMEDELTAH], ins.prev.csr[CSR_HTIMEDELTA]} {
            bins zero = {64'h0};
        }
    `endif
    menvcfg_stce : coverpoint `SSTCHSM_MSTCE;
    henvcfg_stce : coverpoint `SSTCHSM_HSTCE;
    menvcfg_stce_one : coverpoint `SSTCHSM_MSTCE {
        bins one = {1};
    }
    henvcfg_stce_zero : coverpoint `SSTCHSM_HSTCE {
        bins zero = {0};
    }
    henvcfg_stce_one : coverpoint `SSTCHSM_HSTCE {
        bins one = {1};
    }
    mcounteren_tm : coverpoint ins.prev.csr[CSR_MCOUNTEREN][1];
    hcounteren_tm : coverpoint ins.prev.csr[CSR_HCOUNTEREN][1];
    mcounteren_tm_zero : coverpoint ins.prev.csr[CSR_MCOUNTEREN][1] {
        bins zero = {0};
    }
    hcounteren_tm_zero : coverpoint ins.prev.csr[CSR_HCOUNTEREN][1] {
        bins zero = {0};
    }
    hvip_vstip    : coverpoint ins.prev.csr[CSR_HVIP][6];
    hideleg_vstip : coverpoint ins.prev.csr[CSR_HIDELEG][6];
    hie_vstie_one : coverpoint ins.prev.csr[CSR_HIE][6] {
        bins one = {1};
    }

    // hip.VSTIP is hvip.VSTIP | (menvcfg.STCE & henvcfg.STCE & time + htimedelta >= vstimecmp)
    cp_vstip: cross priv_mode_m, csrr, hip, menvcfg_stce, henvcfg_stce, hvip_vstip, vstimecmp_val, htimedelta_zero {
        // henvcfg.STCE is read-only zero while menvcfg.STCE = 0
        ignore_bins stce = binsof(menvcfg_stce) intersect {0} && binsof(henvcfg_stce) intersect {1};
    }
    cp_htimedelta: cross priv_mode_m, csrr, hip, menvcfg_stce_one, henvcfg_stce_one, htimedelta_val, vstimecmp_delta;

    // M-mode reaches vstimecmp whatever the enables hold
    cp_m_vstimecmp_accessible: cross priv_mode_m, csrr, vstimecmp, menvcfg_stce, henvcfg_stce, mcounteren_tm,
                                     hcounteren_tm {
        ignore_bins stce = binsof(menvcfg_stce) intersect {0} && binsof(henvcfg_stce) intersect {1};
    }
    // menvcfg.STCE = 1 with henvcfg.STCE = mcounteren.TM = hcounteren.TM = 0
    cp_m_vstimecmp_accesses: cross priv_mode_m, csraccesses, vstimecmp, menvcfg_stce_one, henvcfg_stce_zero,
                                   mcounteren_tm_zero, hcounteren_tm_zero;

    // vstimecmp armed from M-mode at once or soon with hie.VSTIE = 1 raises VSTI in HS-mode or, delegated, STI in
    // VS-mode.  vstimecmp = 0 arms it at once; time + htimedelta + delay arms it soon; all 1s disarms it
    vstimecmp_arm : coverpoint (ins.current.rs1_val == 0 ? 0 : ins.current.rs1_val == '1 ? 2 : 1) {
        bins now  = {0};
        bins soon = {1};
    }
    cp_vstimecmp_int: cross priv_mode_m, csrrw, vstimecmp_low, vstimecmp_arm, hideleg_vstip, hie_vstie_one,
                            menvcfg_stce_one, henvcfg_stce_one;
endgroup

function void sstchsm_sample(int hart, int issue, ins_t ins);
    SstcHSm_m_cg.sample(ins);
endfunction
