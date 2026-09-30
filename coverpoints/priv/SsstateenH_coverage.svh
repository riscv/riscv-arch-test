///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Ssstateen hypervisor tests executed in HS, VS and VU modes.
// Written: David_Harris@hmc.edu 29 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SSSTATEENH

// hstateen0 SE0 and ENVCFG are in hstateen0h on RV32
`ifdef UDB_MXLEN_64
    `define SSSTATEENH_HSTATEEN0_HI "hstateen0"
`else
    `define SSSTATEENH_HSTATEEN0_HI "hstateen0h"
`endif

// hstateen0 C, FCSR and JVT can be nonzero only when sstateen0 has state to control
`ifdef ZCMT_SUPPORTED
    `define SSSTATEENH_LOW_WRITABLE
`endif
`ifdef ZFINX_SUPPORTED
    `define SSSTATEENH_LOW_WRITABLE
`endif

// A CSR read, the CSRs it targets, and hstateen0.SE0 and hstateen0.ENVCFG before the instruction
`define SSSTATEENH_COMMON \
    csrr : coverpoint ins.current.insn { \
        wildcard bins csrr = {CSRR}; \
    } \
    sstateen0 : coverpoint ins.current.insn[31:20] { \
        bins sstateen0 = {CSR_SSTATEEN0}; \
    } \
    senvcfg : coverpoint ins.current.insn[31:20] { \
        bins senvcfg = {CSR_SENVCFG}; \
    } \
    hstateen0_se0 : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSSTATEENH_HSTATEEN0_HI, "se0") { \
        bins zero = {0}; \
        bins one  = {1}; \
    } \
    hstateen0_envcfg : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSSTATEENH_HSTATEEN0_HI, \
                                              "envcfg") { \
        bins zero = {0}; \
        bins one  = {1}; \
    } \
    stateen123 : coverpoint ins.current.insn[31:20] { \
        bins sstateen1 = {CSR_SSTATEEN1}; \
        bins sstateen2 = {CSR_SSTATEEN2}; \
        bins sstateen3 = {CSR_SSTATEEN3}; \
        bins hstateen1 = {CSR_HSTATEEN1}; \
        bins hstateen2 = {CSR_HSTATEEN2}; \
        bins hstateen3 = {CSR_HSTATEEN3}; \
        `ifdef UDB_MXLEN_32 \
            bins hstateen1h = {CSR_HSTATEEN1H}; \
            bins hstateen2h = {CSR_HSTATEEN2H}; \
            bins hstateen3h = {CSR_HSTATEEN3H}; \
        `endif \
    } \
    hstateen0 : coverpoint ins.current.insn[31:20] { \
        bins hstateen0 = {CSR_HSTATEEN0}; \
        `ifdef UDB_MXLEN_32 \
            bins hstateen0h = {CSR_HSTATEEN0H}; \
        `endif \
    }

covergroup SsstateenH_hs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SSSTATEENH_COMMON

    csrop: coverpoint ins.current.insn {
        wildcard bins csrrs = {CSRRS};
        wildcard bins csrrc = {CSRRC};
    }
    walking_ones: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    // Walk hstateen0 (and hstateen0h) with mstateen0 as at boot
    cp_hs_hstateen0_walk: cross priv_mode_hs, csrop, hstateen0, walking_ones;
    // hstateen0 does not control HS-mode
    cp_hs_sstateen0:      cross priv_mode_hs, csrr, sstateen0, hstateen0_se0;
    cp_hs_senvcfg:        cross priv_mode_hs, csrr, senvcfg, hstateen0_envcfg;
    // Bit 63 of the matching mstateen CSR controls HS-mode access
    cp_hs_stateen123:     cross priv_mode_hs, csrr, stateen123;
endgroup

covergroup SsstateenH_vs_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SSSTATEENH_COMMON

    // Virtual instruction when the hstateen0 bit is 0
    cp_vs_sstateen0:      cross priv_mode_vs, csrr, sstateen0, hstateen0_se0;
    cp_vs_senvcfg:        cross priv_mode_vs, csrr, senvcfg, hstateen0_envcfg;
    // Bit 63 of the matching mstateen and hstateen CSRs controls VS-mode access to sstateen1-3; hstateen is never
    // accessible
    cp_vs_stateen123:     cross priv_mode_vs, csrr, stateen123;
    cp_vs_hstateen0:      cross priv_mode_vs, csrr, hstateen0;

    // sstateen0 bits whose hstateen0 bit is 0 read as zero in VS-mode
    hstateen0_se0_one : coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, `SSSTATEENH_HSTATEEN0_HI, "se0") {
        bins one = {1};
    }
    hstateen0_low : coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "jvt") == 1,
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "fcsr") == 1,
                                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "c") == 1} {
        bins zero = {0};
        `ifdef SSSTATEENH_LOW_WRITABLE
            bins nonzero = {[1:7]};
        `endif
    }
    cp_vs_sstateen0_roz:  cross priv_mode_vs, csrr, sstateen0, hstateen0_se0_one, hstateen0_low;
endgroup

covergroup SsstateenH_vu_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    `SSSTATEENH_COMMON

    // Always virtual instruction when HS-mode could make the access
    cp_vu_sstateen0:      cross priv_mode_vu, csrr, sstateen0, hstateen0_se0;
    cp_vu_senvcfg:        cross priv_mode_vu, csrr, senvcfg, hstateen0_envcfg;
    cp_vu_stateen123:     cross priv_mode_vu, csrr, stateen123;
    cp_vu_hstateen0:      cross priv_mode_vu, csrr, hstateen0;
endgroup

function void ssstateenh_sample(int hart, int issue, ins_t ins);
    SsstateenH_hs_cg.sample(ins);
    SsstateenH_vs_cg.sample(ins);
    SsstateenH_vu_cg.sample(ins);
endfunction
