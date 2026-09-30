///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smstateen hypervisor tests executed in HS, VS and VU modes.
// Written: David_Harris@hmc.edu 29 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SMSTATEENH

// mstateen0 and hstateen0 SE0, ENVCFG and P1P13 are in the high-half CSRs on RV32
`ifdef UDB_MXLEN_64
    `define SMSTATEENH_MSTATEEN0_HI "mstateen0"
    `define SMSTATEENH_HSTATEEN0_HI "hstateen0"
`else
    `define SMSTATEENH_MSTATEEN0_HI "mstateen0h"
    `define SMSTATEENH_HSTATEEN0_HI "hstateen0h"
`endif

// A CSR read, the CSRs each mstateen0 bit controls, and mstateen0 and hstateen0 SE0 and ENVCFG before the
// instruction.  An hstateen0 bit is read-only zero while its mstateen0 bit is 0.
`define SMSTATEENH_COMMON \
    csrr : coverpoint ins.current.insn { \
        wildcard bins csrr = {CSRR}; \
    } \
    se0_csrs : coverpoint ins.current.insn[31:20] { \
        bins sstateen0 = {CSR_SSTATEEN0}; \
        bins hstateen0 = {CSR_HSTATEEN0}; \
        `ifdef UDB_MXLEN_32 \
            bins hstateen0h = {CSR_HSTATEEN0H}; \
        `endif \
    } \
    envcfg_csrs : coverpoint ins.current.insn[31:20] { \
        bins senvcfg = {CSR_SENVCFG}; \
        bins henvcfg = {CSR_HENVCFG}; \
        `ifdef UDB_MXLEN_32 \
            bins henvcfgh = {CSR_HENVCFGH}; \
        `endif \
    } \
    mstateen0_se0 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SMSTATEENH_MSTATEEN0_HI, "se0") { \
        bins zero = {0}; \
        bins one  = {1}; \
    } \
    hstateen0_se0 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SMSTATEENH_HSTATEEN0_HI, "se0") { \
        bins zero = {0}; \
        bins one  = {1}; \
    } \
    mstateen0_envcfg : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SMSTATEENH_MSTATEEN0_HI, \
                                              "envcfg") { \
        bins zero = {0}; \
        bins one  = {1}; \
    } \
    hstateen0_envcfg : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SMSTATEENH_HSTATEEN0_HI, \
                                              "envcfg") { \
        bins zero = {0}; \
        bins one  = {1}; \
    }

`define SMSTATEENH_ROZ(m, h) \
    ignore_bins hstateen0_roz = binsof(m) intersect {0} && binsof(h) intersect {1};

// hedelegh exists only on RV32, and mstateen0.P1P13 controls it
`ifdef UDB_MXLEN_32
    `ifdef SM1P13P0_OR_LATER_SUPPORTED
        `define SMSTATEENH_P1P13
    `endif
`endif
`define SMSTATEENH_P1P13_COVERPOINTS \
    hedelegh : coverpoint ins.current.insn[31:20] { \
        bins hedelegh = {CSR_HEDELEGH}; \
    } \
    mstateen0_p1p13 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0h", "p1p13") { \
        bins zero = {0}; \
        bins one  = {1}; \
    }

covergroup SmstateenH_hs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SMSTATEENH_COMMON

    // Illegal instruction when the mstateen0 bit is 0
    cp_hs_mstateen0_se0:    cross priv_mode_hs, csrr, se0_csrs, mstateen0_se0, hstateen0_se0 {
        `SMSTATEENH_ROZ(mstateen0_se0, hstateen0_se0)
    }
    cp_hs_mstateen0_envcfg: cross priv_mode_hs, csrr, envcfg_csrs, mstateen0_envcfg, hstateen0_envcfg {
        `SMSTATEENH_ROZ(mstateen0_envcfg, hstateen0_envcfg)
    }

    // Walk hstateen0 (and hstateen0h) with only mstateen0.SE0 set (ENVCFG = 0), then with every bit set
    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }
    hstateen0 : coverpoint ins.current.insn[31:20] {
        bins hstateen0 = {CSR_HSTATEEN0};
        `ifdef UDB_MXLEN_32
            bins hstateen0h = {CSR_HSTATEEN0H};
        `endif
    }
    mstateen0_envcfg_zero : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SMSTATEENH_MSTATEEN0_HI,
                                                   "envcfg") {
        bins zero = {0};
    }
    mstateen0_envcfg_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SMSTATEENH_MSTATEEN0_HI,
                                                  "envcfg") {
        bins one = {1};
    }
    cp_hs_hstateen0_roz:  cross priv_mode_hs, csrop, hstateen0, walking_ones, mstateen0_envcfg_zero;
    cp_hs_hstateen0_walk: cross priv_mode_hs, csrop, hstateen0, walking_ones, mstateen0_envcfg_one;
endgroup

covergroup SmstateenH_vs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SMSTATEENH_COMMON

    // Illegal instruction when the mstateen0 bit is 0, else virtual instruction for the H CSRs and for the S CSRs
    // when the hstateen0 bit is 0
    cp_vs_mstateen0_se0:    cross priv_mode_vs, csrr, se0_csrs, mstateen0_se0, hstateen0_se0 {
        `SMSTATEENH_ROZ(mstateen0_se0, hstateen0_se0)
    }
    cp_vs_mstateen0_envcfg: cross priv_mode_vs, csrr, envcfg_csrs, mstateen0_envcfg, hstateen0_envcfg {
        `SMSTATEENH_ROZ(mstateen0_envcfg, hstateen0_envcfg)
    }
    `ifdef SMSTATEENH_P1P13
        `SMSTATEENH_P1P13_COVERPOINTS
        cp_vs_mstateen0_p1p13: cross priv_mode_vs, csrr, hedelegh, mstateen0_p1p13;
    `endif
endgroup

covergroup SmstateenH_vu_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SMSTATEENH_COMMON

    // Illegal instruction when the mstateen0 bit is 0, else virtual instruction
    cp_vu_mstateen0_se0:    cross priv_mode_vu, csrr, se0_csrs, mstateen0_se0, hstateen0_se0 {
        `SMSTATEENH_ROZ(mstateen0_se0, hstateen0_se0)
    }
    cp_vu_mstateen0_envcfg: cross priv_mode_vu, csrr, envcfg_csrs, mstateen0_envcfg, hstateen0_envcfg {
        `SMSTATEENH_ROZ(mstateen0_envcfg, hstateen0_envcfg)
    }
    `ifdef SMSTATEENH_P1P13
        `SMSTATEENH_P1P13_COVERPOINTS
        cp_vu_mstateen0_p1p13: cross priv_mode_vu, csrr, hedelegh, mstateen0_p1p13;
    `endif
endgroup

function void smstateenh_sample(int hart, int issue, ins_t ins);
    SmstateenH_hs_cg.sample(ins);
    SmstateenH_vs_cg.sample(ins);
    SmstateenH_vu_cg.sample(ins);
endfunction
