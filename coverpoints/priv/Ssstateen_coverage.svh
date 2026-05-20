///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
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

    `ifdef XLEN64
    csr_walk: coverpoint ins.current.rs1_val {
            // bits [3:63] are WRPI
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
            // bits [3:31] are WRPI
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

    se0_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "SE0") {
            bins se0_disabled = {1'b0};
            bins se0_enabled  = {1'b1};
    }
    sstateen0_fcsr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "sstateen0", "fcsr") {
            bins fcsr_zero = {1'b0};
            bins fcsr_one  = {1'b1};
    }
    `ifdef ZFINX_SUPPORTED
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
     `ifdef ZCMT_SUPPORTED
        jvt_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "sstateen0", "jvt") {
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
                ignore_bins ig2 = binsof(misa_F.F_clear)  && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig3 = binsof(se0_state.se0_disabled);
        }
        cp_fcsr_lower_fp_instrs: cross priv_mode_u, misa_F, se0_state, sstateen0_fcsr_bit, fp_instrs {
                ignore_bins ig1 = binsof(misa_F.F_set)   && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig2 = binsof(misa_F.F_clear)  && binsof(sstateen0_fcsr_bit.fcsr_zero);
                ignore_bins ig3 = binsof(se0_state.se0_disabled);
        }
    `endif
    cp_mstateen0_se0_controls_sstateen0: cross csrrw, se0_state, sstateen_csrs {
            ignore_bins ig1 = binsof(sstateen_csrs.sstateen1);
            ignore_bins ig2 = binsof(sstateen_csrs.sstateen2);
            ignore_bins ig3 = binsof(sstateen_csrs.sstateen3);
    }
    cp_csr_illegal_accesses: cross priv_mode_u, csr, csrops, se0_state;
    cp_walking_ones:         cross csr, csrops, csr_walk, se0_state;
    `ifdef ZCMT_SUPPORTED
        cp_jvt:                  cross csrrw, jvt_csr, jvt_state, se0_state;
        cp_jvt_lower_mode:       cross priv_mode_u, csrops, jvt_csr, jvt_state, se0_state;
    `endif

endgroup
function void ssstateen_sample(int hart, int issue, ins_t ins);
    Ssstateen_cg.sample(ins);
endfunction
