///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Sstc hypervisor tests executed in HS, VS, VU and U modes.
// Written: David_Harris@hmc.edu 25 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSTCH

// menvcfg.STCE and henvcfg.STCE before the instruction, and the CSR accessed
`ifdef UDB_MXLEN_64
    `define SSTCH_MSTCE ins.prev.csr[CSR_MENVCFG][63]
    `define SSTCH_HSTCE ins.prev.csr[CSR_HENVCFG][63]
    `define SSTCH_TIMECMPS \
        vstimecmp : coverpoint ins.current.insn[31:20] { \
            bins vstimecmp = {CSR_VSTIMECMP}; \
        } \
        stimecmp : coverpoint ins.current.insn[31:20] { \
            bins stimecmp = {CSR_STIMECMP}; \
        }
`else
    `define SSTCH_MSTCE ins.prev.csr[CSR_MENVCFGH][31]
    `define SSTCH_HSTCE ins.prev.csr[CSR_HENVCFGH][31]
    `define SSTCH_TIMECMPS \
        vstimecmp : coverpoint ins.current.insn[31:20] { \
            bins vstimecmp  = {CSR_VSTIMECMP}; \
            bins vstimecmph = {CSR_VSTIMECMPH}; \
        } \
        stimecmp : coverpoint ins.current.insn[31:20] { \
            bins stimecmp  = {CSR_STIMECMP}; \
            bins stimecmph = {CSR_STIMECMPH}; \
        }
`endif

// menvcfg.STCE, henvcfg.STCE, mcounteren.TM and hcounteren.TM before the instruction, and the CSR accessed
`define SSTCH_ENABLES \
    `SSTCH_TIMECMPS \
    menvcfg_stce  : coverpoint `SSTCH_MSTCE; \
    henvcfg_stce  : coverpoint `SSTCH_HSTCE; \
    mcounteren_tm : coverpoint ins.prev.csr[CSR_MCOUNTEREN][1]; \
    hcounteren_tm : coverpoint ins.prev.csr[CSR_HCOUNTEREN][1]; \
    csrr : coverpoint ins.current.insn { \
        wildcard bins csrr = {CSRR}; \
    }

// Accesses of csr_access_test: csrrw all 1s, csrrw 0s, csrrs all 1s, csrrc all 1s, csrr
`define SSTCH_ACCESSES \
    csraccesses : coverpoint ins.current.insn { \
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); \
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); \
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); \
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); \
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); \
    } \
    menvcfg_stce_one : coverpoint `SSTCH_MSTCE { \
        bins one = {1}; \
    } \
    mcounteren_tm_one : coverpoint ins.prev.csr[CSR_MCOUNTEREN][1] { \
        bins one = {1}; \
    }

// henvcfg.STCE is read-only zero while menvcfg.STCE = 0
`define SSTCH_REACHABLE \
    ignore_bins stce = binsof(menvcfg_stce) intersect {0} && binsof(henvcfg_stce) intersect {1};

covergroup SstcH_hs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SSTCH_ENABLES
    `SSTCH_ACCESSES

    // HS-mode reaches vstimecmp only with menvcfg.STCE = mcounteren.TM = 1
    cp_hs_vstimecmp_accessible: cross priv_mode_hs, csrr, vstimecmp, menvcfg_stce, henvcfg_stce, mcounteren_tm,
                                      hcounteren_tm {
        `SSTCH_REACHABLE
    }
    // menvcfg.STCE = mcounteren.TM = 1 with henvcfg.STCE = hcounteren.TM = 0
    henvcfg_stce_zero : coverpoint `SSTCH_HSTCE {
        bins zero = {0};
    }
    hcounteren_tm_zero : coverpoint ins.prev.csr[CSR_HCOUNTEREN][1] {
        bins zero = {0};
    }
    cp_hs_vstimecmp_accesses: cross priv_mode_hs, csraccesses, vstimecmp, menvcfg_stce_one, henvcfg_stce_zero,
                                    mcounteren_tm_one, hcounteren_tm_zero;

    // vstimecmp armed at once or soon with hie.VSTIE = 1 raises VSTI in HS-mode or, delegated, STI in VS-mode
    csrrw : coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    vstimecmp_low : coverpoint ins.current.insn[31:20] {
        bins vstimecmp = {CSR_VSTIMECMP};
    }
    // vstimecmp = 0 arms it at once; time + htimedelta + delay arms it soon; all 1s disarms it
    vstimecmp_arm : coverpoint (ins.current.rs1_val == 0 ? 0 : ins.current.rs1_val == '1 ? 2 : 1) {
        bins now  = {0};
        bins soon = {1};
    }
    hideleg_vstip : coverpoint ins.prev.csr[CSR_HIDELEG][6];
    hie_vstie_one : coverpoint ins.prev.csr[CSR_HIE][6] {
        bins one = {1};
    }
    henvcfg_stce_one : coverpoint `SSTCH_HSTCE {
        bins one = {1};
    }
    cp_vstimecmp_int: cross priv_mode_hs, csrrw, vstimecmp_low, vstimecmp_arm, hideleg_vstip, hie_vstie_one,
                            menvcfg_stce_one, henvcfg_stce_one;
endgroup

covergroup SstcH_vs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SSTCH_ENABLES
    `SSTCH_ACCESSES

    // stimecmp is vstimecmp in VS-mode, gated by both STCE and both TM bits
    cp_vs_stimecmp_accessible: cross priv_mode_vs, csrr, stimecmp, menvcfg_stce, henvcfg_stce, mcounteren_tm,
                                     hcounteren_tm {
        `SSTCH_REACHABLE
    }
    // vstimecmp by its own address is never accessible in VS-mode
    cp_vs_vstimecmp_inaccessible: cross priv_mode_vs, csrr, vstimecmp, menvcfg_stce, henvcfg_stce, mcounteren_tm,
                                        hcounteren_tm {
        `SSTCH_REACHABLE
    }
    henvcfg_stce_one : coverpoint `SSTCH_HSTCE {
        bins one = {1};
    }
    hcounteren_tm_one : coverpoint ins.prev.csr[CSR_HCOUNTEREN][1] {
        bins one = {1};
    }
    cp_vs_stimecmp_accesses: cross priv_mode_vs, csraccesses, stimecmp, menvcfg_stce_one, henvcfg_stce_one,
                                   mcounteren_tm_one, hcounteren_tm_one;
endgroup

covergroup SstcH_vu_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SSTCH_ENABLES

    timecmp : coverpoint ins.current.insn[31:20] {
        bins stimecmp  = {CSR_STIMECMP};
        bins vstimecmp = {CSR_VSTIMECMP};
        `ifdef UDB_MXLEN_32
            bins stimecmph  = {CSR_STIMECMPH};
            bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
    }
    // Illegal instruction when HS-mode could not access them, else virtual instruction
    cp_vu_timecmp_inaccessible: cross priv_mode_vu, csrr, timecmp, menvcfg_stce, henvcfg_stce, mcounteren_tm,
                                      hcounteren_tm {
        `SSTCH_REACHABLE
    }
endgroup

covergroup SstcH_u_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SSTCH_ENABLES

    timecmp : coverpoint ins.current.insn[31:20] {
        bins stimecmp  = {CSR_STIMECMP};
        bins vstimecmp = {CSR_VSTIMECMP};
        `ifdef UDB_MXLEN_32
            bins stimecmph  = {CSR_STIMECMPH};
            bins vstimecmph = {CSR_VSTIMECMPH};
        `endif
    }
    // Always illegal instruction
    cp_u_timecmp_inaccessible: cross priv_mode_u, csrr, timecmp, menvcfg_stce, henvcfg_stce, mcounteren_tm,
                                     hcounteren_tm {
        `SSTCH_REACHABLE
    }
endgroup

function void sstch_sample(int hart, int issue, ins_t ins);
    SstcH_hs_cg.sample(ins);
    SstcH_vs_cg.sample(ins);
    SstcH_vu_cg.sample(ins);
    SstcH_u_cg.sample(ins);
endfunction
