///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SSSTATEEN
covergroup Ssstateen_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"
    csrops: coverpoint ins.current.insn {
            wildcard bins csrw = {CSRRW};
            wildcard bins csrr = {CSRR};
            wildcard bins csrs = {CSRRS};
            wildcard bins csrc = {CSRRC};
    }
    sstateen_csrs: coverpoint ins.current.insn[31:20] {
            bins sstateen0 = {CSR_SSTATEEN0};
            bins sstateen1 = {CSR_SSTATEEN1};
            bins sstateen2 = {CSR_SSTATEEN2};
            bins sstateen3 = {CSR_SSTATEEN3};
    }

    `ifdef UDB_MXLEN_64
    csr_walk: coverpoint ins.current.rs1_val {
            // bits [3:63] are WPRI; bit 0 (C) is readonly-zero
            `ifdef ZFINX_SUPPORTED
                wildcard bins walking1_1  = {64'b??????????????????????????????????????????????????????????????1?};
            `endif
            `ifdef ZCMT_SUPPORTED
                wildcard bins walking1_2  = {64'b?????????????????????????????????????????????????????????????1??};
            `endif
            wildcard bins walking0_1  = {64'b??????????????????????????????????????????????????????????????0?};
            wildcard bins walking0_2  = {64'b?????????????????????????????????????????????????????????????0??};
    }
    `else
    csr_walk: coverpoint ins.current.csr[ins.current.insn[31:20]] {
            // bits [3:31] are WPRI; bit 0 (C) is readonly-zero
            `ifdef ZFINX_SUPPORTED
                wildcard bins walking1_1  = {32'b??????????????????????????????1?};
            `endif
            `ifdef ZCMT_SUPPORTED
                wildcard bins walking1_2  = {32'b?????????????????????????????1??};
            `endif
            wildcard bins walking0_1  = {32'b??????????????????????????????0?};
            wildcard bins walking0_2  = {32'b?????????????????????????????0??};
    }
    `endif

    // SE0 is bit 63 of mstateen0 on RV64, bit 31 of mstateen0h on RV32
    `ifdef UDB_MXLEN_64
        se0_state: coverpoint ins.current.csr[CSR_MSTATEEN0][63] {
                bins se0_enabled  = {1'b1};
        }
    `else
        se0_state: coverpoint ins.current.csr[CSR_MSTATEEN0H][31] {
                bins se0_enabled  = {1'b1};
        }
    `endif

    `ifdef ZFINX_SUPPORTED
        sstateen0_fcsr_bit: coverpoint ins.current.csr[CSR_SSTATEEN0][1] {
                bins fcsr_zero = {1'b0};
                bins fcsr_one  = {1'b1};
        }
        fcsr_lower_mode_csrs: coverpoint ins.current.csr[31:20] {
                wildcard bins frm    = {CSR_FRM};
                wildcard bins fflags = {CSR_FFLAGS};
                wildcard bins fcsr   = {CSR_FCSR};
        }
        fp_instrs: coverpoint ins.current.insn {
                wildcard bins fadd_s   = {FADD_S};
                wildcard bins flw      = {FLW};
                wildcard bins fcvt_ws  = {FCVT_W_S};
                wildcard bins fcvt_sw  = {FCVT_S_W};
                wildcard bins fmv_xw   = {FMV_X_W};
                wildcard bins fmv_wx   = {FMV_W_X};
                wildcard bins fclass_s = {FCLASS_S};
        }
    `endif
    `ifdef ZCMT_SUPPORTED
        jvt_state: coverpoint ins.current.csr[CSR_SSTATEEN0][2] {
                bins jvt_disabled = {1'b0};
                bins jvt_enabled  = {1'b1};
        }
        jvt_csr: coverpoint ins.current.csr[31:20] {
                wildcard bins jvt = {CSR_JVT};
        }
    `endif
    `ifdef ZFINX_SUPPORTED
        cp_fcsr_lower: cross priv_mode_s_u, misa_F, se0_state, sstateen0_fcsr_bit, csrops, fcsr_lower_mode_csrs {
                ignore_bins ig1 = binsof(misa_F.F_set)   && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(sstateen0_fcsr_bit.fcsr_zero);
        }
        cp_fcsr_lower_fp_instrs: cross priv_mode_u, misa_F, se0_state, sstateen0_fcsr_bit, fp_instrs {
                ignore_bins ig1 = binsof(misa_F.F_set)   && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(sstateen0_fcsr_bit.fcsr_zero);
        }
    `endif

    `ifdef UDB_MXLEN_64
        envcfg_state: coverpoint ins.current.csr[CSR_MSTATEEN0][62] {
                bins envcfg_disabled = {1'b0};
                bins envcfg_enabled  = {1'b1};
        }
    `else
        envcfg_state: coverpoint ins.current.csr[CSR_MSTATEEN0H][30] {
                bins envcfg_disabled = {1'b0};
                bins envcfg_enabled  = {1'b1};
        }
    `endif
    senvcfg_csr: coverpoint ins.current.insn[31:20] {
            bins senvcfg = {CSR_SENVCFG};
    }
    `ifdef SSDTRIG_SUPPORTED
    context_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "context") {
        bins context_disabled = {1'b0};
        bins context_enabled  = {1'b1};
    }
    scontext_csr: coverpoint ins.current.insn[31:20] {
        wildcard bins scontext = {CSR_SCONTEXT};
    }
    `endif
    `ifdef SM1P13_SUPPORTED
    p1p13_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "p1p13") {
        bins p1p13_disabled = {1'b0};
        bins p1p13_enabled  = {1'b1};
    }
    hedelegh_csr: coverpoint ins.current.insn[31:20] {
        wildcard bins hedelegh = {CSR_HEDELEGH};
    }
    `endif
    `ifdef IMSIC_SUPPORTED
        imsic_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "imsic") {
            bins imsic_disabled = {1'b0};
            bins imsic_enabled  = {1'b1};
        }
        imsic_csrs: coverpoint ins.current.insn[31:20] {
            wildcard bins stopei = {CSR_STOPEI};
            wildcard bins vstopei = {CSR_VSTOPEI};
        }
    `endif
    `ifdef AIA_SUPPORTED
        aia_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "aia") {
            bins aia_disabled = {1'b0};
            bins aia_enabled  = {1'b1};
        }
        aia_csrs: coverpoint ins.current.insn[31:20] {
            `ifdef XLEN64
                wildcard bins aia_m = {CSR_SIE};
                wildcard bins aia_s = {CSR_SIP};
            `endif
            `ifdef XLEN32
                bins aia_m = {CSR_SIEH};
                bins aia_s = {CSR_SIPH};
            `endif
        }
    `endif
    cp_mstateen0_se0_controls_sstateen0: cross csrops, se0_state, sstateen_csrs {
            ignore_bins ig1 = binsof(sstateen_csrs.sstateen1);
            ignore_bins ig2 = binsof(sstateen_csrs.sstateen2);
            ignore_bins ig3 = binsof(sstateen_csrs.sstateen3);
    }
    cp_csr_illegal_accesses: cross priv_mode_u, sstateen_csrs, csrops, se0_state;
    cp_walking_ones:         cross sstateen_csrs, csrops, csr_walk, se0_state;
    `ifdef ZCMT_SUPPORTED
        cp_jvt:              cross csrops, jvt_csr, jvt_state, se0_state;
        cp_jvt_lower_mode:   cross priv_mode_u, csrops, jvt_csr, jvt_state, se0_state;
    `endif

        cp_envcfg: cross csrops, senvcfg_csr, envcfg_state, priv_mode_s;
    `ifdef SSDTRIG_SUPPORTED
        cp_context: cross csrops, scontext_csr, context_state, priv_mode_s;
    `endif
    `ifdef SM1P13_SUPPORTED
        cp_p1p13: cross csrops, p1p13_state, hedelegh_csr, priv_mode_s;
    `endif
    `ifdef SCTR_SUPPORTED
        cp_ctr: cross csrops, ctr_csrs, ctr_state, priv_mode_s;
    `endif
    `ifdef IMSIC_SUPPORTED
        cp_imsic: cross csrops, imsic_csrs, imsic_state, priv_mode_s;
    `endif
    `ifdef AIA_SUPPORTED
        cp_aia: cross csrops, aia_csrs, aia_state, priv_mode_s;
    `endif

endgroup
function void ssstateen_sample(int hart, int issue, ins_t ins);
    Ssstateen_cg.sample(ins);
endfunction
