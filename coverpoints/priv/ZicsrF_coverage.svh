///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZICSRF
covergroup ZicsrF_cg with function sample(ins_t ins);

    fcsrname : coverpoint ins.current.insn[31:20] {
        bins fcsr    = {CSR_FCSR};
        bins frm     = {CSR_FRM};
        bins fflags  = {CSR_FFLAGS};
    }

    csraccesses : coverpoint ins.current.insn {
        wildcard bins csrrc_all = {CSRRC} iff (ins.current.rs1_val == '1); // csrc all ones
        wildcard bins csrrw0    = {CSRRW} iff (ins.current.rs1_val ==  0); // csrw all zeros
        wildcard bins csrrw1    = {CSRRW} iff (ins.current.rs1_val == '1); // csrw all ones
        wildcard bins csrrs_all = {CSRRS} iff (ins.current.rs1_val == '1); // csrs all ones
        wildcard bins csrr      = {CSRR}  iff (ins.current.rs1_val ==  0); // csrr
    }

    // building blocks for the main coverpoints
    csrrw: coverpoint ins.current.insn {
        wildcard bins csrrw = {CSRRW};
    }
    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }
    fcsr: coverpoint ins.current.insn[31:20] {
        bins fcsr = {CSR_FCSR};
    }
    frm: coverpoint ins.current.insn[31:20] {
        bins frm = {CSR_FRM};
    }
    fflags: coverpoint ins.current.insn[31:20] {
        bins fflags = {CSR_FFLAGS};
    }
    // csrrw/csrrs/csrrc that write (rs1 != x0) and return the old value in rd != x0
    csr_swap_op: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011 & ins.current.insn[19:15] != 5'b00000) {
        bins csrrw = {3'b001};
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }
    rd_nonzero: coverpoint ins.current.insn[11:7] iff (ins.current.rd_val != 0) { // old value is nonzero
        bins nonzero = {[1:31]};
    }
    fcsr_frm_edges: coverpoint ins.current.rs1_val[7:5] {
        // auto fills 0 through 7
    }
    frm_edges: coverpoint ins.current.rs1_val[2:0] {
        // auto fills 0 through 7
    }
    fflags_edges: coverpoint ins.current.rs1_val[4:0] {
        // auto fills 0 through 15
    }
    walking_ones : coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b_1[] = { [0:`UDB_MXLEN-1] };
    }

    fadd: coverpoint ins.current.insn {
        wildcard bins fadd = {FADD_S};
    }//                                 ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ assumes single precision since there isn't a good
    //                                                                      way to specify the fs1 and fs2 values otherwise
    fsub: coverpoint ins.current.insn {
        wildcard bins fsub = {FSUB_S};
    }
    fdiv: coverpoint ins.current.insn {
        wildcard bins fdiv = {FDIV_S};
    }
    fmul: coverpoint ins.current.insn {
        wildcard bins fmul = {FMUL_S};
    }
    fs2_zero: coverpoint ins.current.fs2_val[31:0] {
        bins zero = {32'h00000000};
    }
    fs1_one: coverpoint ins.current.fs1_val[31:0] {
        bins one = {32'h3f800000};
    }
    fs2_three: coverpoint ins.current.fs2_val[31:0] {
        bins three = {32'h40400000};
    }
    fs1_largest: coverpoint ins.current.fs1_val[31:0] {
        bins largest = {32'h7f7fffff};
    }
    fs2_largest: coverpoint ins.current.fs2_val[31:0] {
        bins largest = {32'h7f7fffff};
    }
    fs1_smallest: coverpoint ins.current.fs1_val[31:0] {
        bins smallest = {32'h00800000};
    }
    fs2_smallest: coverpoint ins.current.fs2_val[31:0] {
        bins smallest = {32'h00800000};
    }
    fs1_infinity: coverpoint ins.current.fs1_val[31:0] {
        bins infinity = {32'h7f800000};
    }
    fs2_infinity: coverpoint ins.current.fs2_val[31:0] {
        bins infinity = {32'h7f800000};
    }

    // main coverpoints
    cp_fcsr_access:           cross fcsrname, csraccesses;
    cp_fcsr_walk:             cross csrop, fcsrname,     walking_ones;
    cp_fcsr_frm_write:        cross csrrw, fcsr,         fcsr_frm_edges;
    cp_fcsr_fflags_write:     cross csrrw, fcsr,         fflags_edges;
    cp_frm_write:             cross csrrw, frm,          frm_edges;
    cp_fflags_write:          cross csrrw, fflags,       fflags_edges;
    cp_fcsr_swap:             cross csr_swap_op, fcsrname, rd_nonzero;
    cp_fflags_set_m_NV:       cross fsub,  fs1_infinity, fs2_infinity;
    cp_fflags_set_m_DZ:       cross fdiv,  fs1_one,      fs2_zero;
    cp_fflags_set_m_OF:       cross fadd,  fs1_largest,  fs2_largest;
    cp_fflags_set_m_UF:       cross fmul,  fs1_smallest, fs2_smallest;
    cp_fflags_set_m_NX:       cross fdiv,  fs1_one,      fs2_three;

    // An instruction with a static rounding mode must not trap when frm holds a reserved value
    frm_reserved: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "frm", "frm") {
        bins reserved[] = {[5:7]};
    }
    static_rm: coverpoint ins.current.insn[14:12] {
        bins rne = {3'b000};
        bins rtz = {3'b001};
        bins rdn = {3'b010};
        bins rup = {3'b011};
        bins rmm = {3'b100};
    }
    // Three adds per mode, whose results together differ in every rounding mode
    frm_reserved_addend: coverpoint ins.current.fs2_val[31:0] {
        bins tie_odd      = {32'h34400000}; // 1 + 1.5*2^-23
        bins tie_even_neg = {32'hB3800000}; // -1 - 2^-24
        bins quarter_ulp  = {32'h33000000}; // 1 + 2^-25
    }
    cp_frm_reserved_static_rm: cross fadd, frm_reserved, static_rm, frm_reserved_addend iff (ins.trap == 0);

    // very specific tests to check that underflow is computed after rounding
    // The operand sets come from Berkeley TestFloat cases whose exact result is tiny before rounding.
    // Each is crossed with every static rounding mode: in some modes the result is not tiny after
    // rounding (UF = 0), in others it is tiny after rounding even though the delivered result is +/-2^emin (UF = 1).
    // fmul_emin: 2^emin * (1 - 2^-p) is tiny after rounding in every mode (UF = 1), though it rounds to +/-2^emin in some.
    // fdiv: (2 - 2^-(p-2)) * 2^emin / (2 - 2^-(p-1)) rounds to +/-2^emin, with UF = 1, when rounding away from zero.
    // fdiv has no tiny-before-but-not-after case: a quotient of p-bit significands is never within 2^-p of 1 unless exact.
    // single-precision (S) cases
    underflow_fma_s: coverpoint ins.current.insn iff
        (ins.current.fs1_val[31:0] == 32'h3F00FBFF & ins.current.fs2_val[31:0] == 32'h80000001 & ins.current.fs3_val[31:0] == 32'h807FFFFF) {
            wildcard bins fmadd = {FMADD_S};
        }
    cp_underflow_after_rounding_fma_s: cross underflow_fma_s, static_rm;

    underflow_fmul_s: coverpoint ins.current.insn iff
        (ins.current.fs1_val[31:0] == 32'h00800001 & ins.current.fs2_val[31:0] == 32'h3F7FFFFE) {
            wildcard bins fmul = {FMUL_S};
        }
    cp_underflow_after_rounding_fmul_s: cross underflow_fmul_s, static_rm;

    underflow_fmul_emin_s: coverpoint ins.current.insn iff
        (ins.current.fs1_val[31:0] == 32'h00800000 & ins.current.fs2_val[31:0] == 32'h3F7FFFFF) {
            wildcard bins fmul = {FMUL_S};
        }
    cp_underflow_after_rounding_fmul_emin_s: cross underflow_fmul_emin_s, static_rm;

    underflow_fdiv_s: coverpoint ins.current.insn iff
        (ins.current.fs1_val[31:0] == 32'h00FFFFFE & ins.current.fs2_val[31:0] == 32'h3FFFFFFF) {
            wildcard bins fdiv = {FDIV_S};
        }
    cp_underflow_after_rounding_fdiv_s: cross underflow_fdiv_s, static_rm;

    `ifdef D_SUPPORTED
    // double-precision (D) cases
        underflow_fma_d: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'h802FFFFFFFBFFEFF & ins.current.fs2_val[63:0] == 64'h000FFFFFFFFFFFFE & ins.current.fs3_val[63:0] == 64'h0010000000000000) {
                wildcard bins fmadd = {FMADD_D};
            }
        cp_underflow_after_rounding_fma_d: cross underflow_fma_d, static_rm;

        underflow_fmul_d: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'h0010000000000001 & ins.current.fs2_val[63:0] == 64'hBFEFFFFFFFFFFFFE) {
                wildcard bins fmul = {FMUL_D};
            }
        cp_underflow_after_rounding_fmul_d: cross underflow_fmul_d, static_rm;

        underflow_fcvt_s_d: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'hB80FFFFFFFFDFEFF) {
                wildcard bins fcvt = {FCVT_S_D};
            }
        cp_underflow_after_rounding_fcvt_s_d: cross underflow_fcvt_s_d, static_rm;

        underflow_fmul_emin_d: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'h8010000000000000 & ins.current.fs2_val[63:0] == 64'h3FEFFFFFFFFFFFFF) {
                wildcard bins fmul = {FMUL_D};
            }
        cp_underflow_after_rounding_fmul_emin_d: cross underflow_fmul_emin_d, static_rm;

        underflow_fdiv_d: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'h801FFFFFFFFFFFFE & ins.current.fs2_val[63:0] == 64'h3FFFFFFFFFFFFFFF) {
                wildcard bins fdiv = {FDIV_D};
            }
        cp_underflow_after_rounding_fdiv_d: cross underflow_fdiv_d, static_rm;
    `endif

    `ifdef Q_SUPPORTED
    // quad-precision (Q) cases
        underflow_fma_q: coverpoint ins.current.insn iff
            (ins.current.fs1_val == 128'h3F9800000000000001FFFFFFFF7FFFFE & ins.current.fs2_val == 128'h00000000000000000000000000000001 & ins.current.fs3_val == 128'h80010000000000000000000000000000) {
                wildcard bins fmadd = {FMADD_Q};
            }
        cp_underflow_after_rounding_fma_q: cross underflow_fma_q, static_rm;

        underflow_fmul_q: coverpoint ins.current.insn iff
            (ins.current.fs1_val == 128'h0000FFFFFFFFFFFFFFFFFFFFFFFFFFFF & ins.current.fs2_val == 128'h3FFF0000000000000000000000000001) {
                wildcard bins fmul = {FMUL_Q};
            }
        cp_underflow_after_rounding_fmul_q: cross underflow_fmul_q, static_rm;

        underflow_fcvt_s_q: coverpoint ins.current.insn iff
            (ins.current.fs1_val == 128'h3F80FFFFFFFE0000000000FFFFFFFFFF) {
                wildcard bins fcvt = {FCVT_S_Q};
            }
        cp_underflow_after_rounding_fcvt_s_q: cross underflow_fcvt_s_q, static_rm;
    `endif

    `ifdef ZFH_SUPPORTED
    // half-precision (H) cases
        underflow_fma_h: coverpoint ins.current.insn iff
            (ins.current.fs1_val[15:0] == 16'h0BC7 & ins.current.fs2_val[15:0] == 16'h03FF & ins.current.fs3_val[15:0] == 16'h8400) {
                wildcard bins fmadd = {FMADD_H};
            }
        cp_underflow_after_rounding_fma_h: cross underflow_fma_h, static_rm;

        underflow_fmul_h: coverpoint ins.current.insn iff
            (ins.current.fs1_val[15:0] == 16'h0401 & ins.current.fs2_val[15:0] == 16'h3BFE) {
                wildcard bins fmul = {FMUL_H};
            }
        cp_underflow_after_rounding_fmul_h: cross underflow_fmul_h, static_rm;

        underflow_fmul_emin_h: coverpoint ins.current.insn iff
            (ins.current.fs1_val[15:0] == 16'h0400 & ins.current.fs2_val[15:0] == 16'h3BFF) {
                wildcard bins fmul = {FMUL_H};
            }
        cp_underflow_after_rounding_fmul_emin_h: cross underflow_fmul_emin_h, static_rm;

        underflow_fdiv_h: coverpoint ins.current.insn iff
            (ins.current.fs1_val[15:0] == 16'h07FE & ins.current.fs2_val[15:0] == 16'h3FFF) {
                wildcard bins fdiv = {FDIV_H};
            }
        cp_underflow_after_rounding_fdiv_h: cross underflow_fdiv_h, static_rm;
    `endif

    `ifdef ZFHMIN_SUPPORTED
        underflow_fcvt_h_s: coverpoint ins.current.insn iff
            (ins.current.fs1_val[31:0] == 32'h387FF000) {
                wildcard bins fcvt = {FCVT_H_S};
            }
        cp_underflow_after_rounding_fcvt_h_s: cross underflow_fcvt_h_s, static_rm;
    `endif

    ///////////////////////////////////////////
    // Directed FP edge cases (ZicsrF_fma, ZicsrF_cvt and ZicsrF_zfa test files).
    // Each crosses a handful of operand values with every static rounding mode; the same crosses
    // in the F, D, Zfh, Zfbfmin and Zfa suites would multiply their size.
    ///////////////////////////////////////////

    // FMA with multiplicands +inf and +0: canonical NaN and NV, even for a quiet NaN addend
    fma_inf_zero_s_op: coverpoint ins.current.insn {
        wildcard bins fmadd = {FMADD_S};
        wildcard bins fmsub = {FMSUB_S};
        wildcard bins fnmadd = {FNMADD_S};
        wildcard bins fnmsub = {FNMSUB_S};
    }
    fma_inf_zero_s_addend: coverpoint ins.current.fs3_val[31:0] iff (ins.current.fs1_val[31:0] == 32'h7F800000 & ins.current.fs2_val[31:0] == 32'h00000000) {
        bins qnan = {32'h7FC00000};
        bins snan = {32'h7F800001};
        bins one = {32'h3F800000};
    }
    cp_fma_inf_zero_s: cross fma_inf_zero_s_op, fma_inf_zero_s_addend;

    // FMA whose product exactly cancels the addend: +0, or -0 under RDN, in every static rounding mode
    fma_exact_zero_s: coverpoint ins.current.insn iff (ins.current.fs1_val[31:0] == 32'h3F800800 & ins.current.fs2_val[31:0] == 32'h3F7FF000) {
        wildcard bins fmadd = {FMADD_S} iff (ins.current.fs3_val[31:0] == 32'hBF7FFFFF);
        wildcard bins fmsub = {FMSUB_S} iff (ins.current.fs3_val[31:0] == 32'h3F7FFFFF);
        wildcard bins fnmadd = {FNMADD_S} iff (ins.current.fs3_val[31:0] == 32'hBF7FFFFF);
        wildcard bins fnmsub = {FNMSUB_S} iff (ins.current.fs3_val[31:0] == 32'h3F7FFFFF);
    }
    cp_fma_exact_zero_s: cross fma_exact_zero_s, static_rm;

    `ifdef D_SUPPORTED
        fma_inf_zero_d_op: coverpoint ins.current.insn {
            wildcard bins fmadd = {FMADD_D};
            wildcard bins fmsub = {FMSUB_D};
            wildcard bins fnmadd = {FNMADD_D};
            wildcard bins fnmsub = {FNMSUB_D};
        }
        fma_inf_zero_d_addend: coverpoint ins.current.fs3_val[63:0] iff (ins.current.fs1_val[63:0] == 64'h7FF0000000000000 & ins.current.fs2_val[63:0] == 64'h0000000000000000) {
            bins qnan = {64'h7FF8000000000000};
            bins snan = {64'h7FF0000000000001};
            bins one = {64'h3FF0000000000000};
        }
        cp_fma_inf_zero_d: cross fma_inf_zero_d_op, fma_inf_zero_d_addend;
    `endif

    `ifdef D_SUPPORTED
        fma_exact_zero_d: coverpoint ins.current.insn iff (ins.current.fs1_val[63:0] == 64'h3FF0000004000000 & ins.current.fs2_val[63:0] == 64'h3FEFFFFFF8000000) {
            wildcard bins fmadd = {FMADD_D} iff (ins.current.fs3_val[63:0] == 64'hBFEFFFFFFFFFFFFE);
            wildcard bins fmsub = {FMSUB_D} iff (ins.current.fs3_val[63:0] == 64'h3FEFFFFFFFFFFFFE);
            wildcard bins fnmadd = {FNMADD_D} iff (ins.current.fs3_val[63:0] == 64'hBFEFFFFFFFFFFFFE);
            wildcard bins fnmsub = {FNMSUB_D} iff (ins.current.fs3_val[63:0] == 64'h3FEFFFFFFFFFFFFE);
        }
        cp_fma_exact_zero_d: cross fma_exact_zero_d, static_rm;
    `endif

    `ifdef ZFH_SUPPORTED
        fma_inf_zero_h_op: coverpoint ins.current.insn {
            wildcard bins fmadd = {FMADD_H};
            wildcard bins fmsub = {FMSUB_H};
            wildcard bins fnmadd = {FNMADD_H};
            wildcard bins fnmsub = {FNMSUB_H};
        }
        fma_inf_zero_h_addend: coverpoint ins.current.fs3_val[15:0] iff (ins.current.fs1_val[15:0] == 16'h7C00 & ins.current.fs2_val[15:0] == 16'h0000) {
            bins qnan = {16'h7E00};
            bins snan = {16'h7C01};
            bins one = {16'h3C00};
        }
        cp_fma_inf_zero_h: cross fma_inf_zero_h_op, fma_inf_zero_h_addend;
    `endif

    `ifdef ZFH_SUPPORTED
        fma_exact_zero_h: coverpoint ins.current.insn iff (ins.current.fs1_val[15:0] == 16'h3C20 & ins.current.fs2_val[15:0] == 16'h3BC0) {
            wildcard bins fmadd = {FMADD_H} iff (ins.current.fs3_val[15:0] == 16'hBBFE);
            wildcard bins fmsub = {FMSUB_H} iff (ins.current.fs3_val[15:0] == 16'h3BFE);
            wildcard bins fnmadd = {FNMADD_H} iff (ins.current.fs3_val[15:0] == 16'hBBFE);
            wildcard bins fnmsub = {FNMSUB_H} iff (ins.current.fs3_val[15:0] == 16'h3BFE);
        }
        cp_fma_exact_zero_h: cross fma_exact_zero_h, static_rm;
    `endif

    `ifdef D_SUPPORTED
        // Narrowing conversions at the overflow threshold, halfway ties and the tininess boundary,
        // under every static rounding mode
        fcvt_s_d_rounding_op: coverpoint ins.current.insn {
            wildcard bins fcvt_s_d = {FCVT_S_D};
        }
        fcvt_s_d_rounding_vals: coverpoint ins.current.fs1_val[63:0] {
            bins ovf_tie = {64'h47EFFFFFF0000000};
            bins ovf_below_neg = {64'hC7EFFFFFEFFFFFFF};
            bins tie_pos = {64'h3FF0000010000000};
            bins tie_neg = {64'hBFF0000010000000};
            bins above_half = {64'h3FF0000018000000};
            bins tiny_tie = {64'h380FFFFFF0000000};
            bins tiny_below = {64'h380FFFFFEFFFFFFF};
        }
        cp_fcvt_s_d_rounding: cross fcvt_s_d_rounding_op, fcvt_s_d_rounding_vals, static_rm;
    `endif

    `ifdef ZFHMIN_SUPPORTED
        fcvt_h_s_rounding_op: coverpoint ins.current.insn {
            wildcard bins fcvt_h_s = {FCVT_H_S};
        }
        fcvt_h_s_rounding_vals: coverpoint ins.current.fs1_val[31:0] {
            bins ovf_tie = {32'h477FF000};
            bins ovf_below_neg = {32'hC77FEFFF};
            bins tie_pos = {32'h3F801000};
            bins tie_neg = {32'hBF801000};
            bins above_half = {32'h3F801800};
            bins tiny_below = {32'h387FEFFF};
        }
        cp_fcvt_h_s_rounding: cross fcvt_h_s_rounding_op, fcvt_h_s_rounding_vals, static_rm;
    `endif

    `ifdef D_SUPPORTED
        `ifdef ZFHMIN_SUPPORTED
            fcvt_h_d_rounding_op: coverpoint ins.current.insn {
                wildcard bins fcvt_h_d = {FCVT_H_D};
            }
            fcvt_h_d_rounding_vals: coverpoint ins.current.fs1_val[63:0] {
                bins ovf_tie = {64'h40EFFE0000000000};
                bins ovf_below_neg = {64'hC0EFFDFFFFFFFFFF};
                bins tie_pos = {64'h3FF0020000000000};
                bins tie_neg = {64'hBFF0020000000000};
                bins above_half = {64'h3FF0030000000000};
                bins tiny_tie = {64'h3F0FFE0000000000};
                bins tiny_below = {64'h3F0FFDFFFFFFFFFF};
            }
            cp_fcvt_h_d_rounding: cross fcvt_h_d_rounding_op, fcvt_h_d_rounding_vals, static_rm;
        `endif
    `endif

    `ifdef ZFBFMIN_SUPPORTED
        fcvt_bf16_s_rounding_op: coverpoint ins.current.insn {
            wildcard bins fcvt_bf16_s = {FCVT_BF16_S};
        }
        fcvt_bf16_s_rounding_vals: coverpoint ins.current.fs1_val[31:0] {
            bins ovf_tie = {32'h7F7F8000};
            bins ovf_below_neg = {32'hFF7F7FFF};
            bins tie_pos = {32'h3F808000};
            bins tie_neg = {32'hBF808000};
            bins above_half = {32'h3F80C000};
            bins tiny_tie = {32'h007FC000};
            bins tiny_below = {32'h007FBFFF};
        }
        cp_fcvt_bf16_s_rounding: cross fcvt_bf16_s_rounding_op, fcvt_bf16_s_rounding_vals, static_rm;
    `endif

    // Integer to floating-point conversions of values that are ties or inexact in the destination,
    // under every static rounding mode
    fcvt_s_w_rounding_op: coverpoint ins.current.insn {
        wildcard bins fcvt_s_w = {FCVT_S_W};
    }
    fcvt_s_w_rounding_vals: coverpoint ins.current.rs1_val[31:0] {
        bins tie_pos = {32'h01000001};
        bins tie_neg = {32'hFEFFFFFF};
        bins above_half = {32'h02000003};
    }
    cp_fcvt_s_w_rounding: cross fcvt_s_w_rounding_op, fcvt_s_w_rounding_vals, static_rm;

    fcvt_s_wu_rounding_op: coverpoint ins.current.insn {
        wildcard bins fcvt_s_wu = {FCVT_S_WU};
    }
    fcvt_s_wu_rounding_vals: coverpoint ins.current.rs1_val[31:0] {
        bins tie_even = {32'h01000001};
        bins tie_odd = {32'h01000003};
        bins quarter_ulp = {32'h02000001};
    }
    cp_fcvt_s_wu_rounding: cross fcvt_s_wu_rounding_op, fcvt_s_wu_rounding_vals, static_rm;

    `ifdef UDB_MXLEN_64
        fcvt_s_l_rounding_op: coverpoint ins.current.insn {
            wildcard bins fcvt_s_l = {FCVT_S_L};
        }
        fcvt_s_l_rounding_vals: coverpoint ins.current.rs1_val[63:0] {
            bins tie_pos = {64'h0000010000010000};
            bins tie_neg = {64'hFFFFFEFFFFFF0000};
            bins above_half = {64'h0000020000030000};
        }
        cp_fcvt_s_l_rounding: cross fcvt_s_l_rounding_op, fcvt_s_l_rounding_vals, static_rm;
    `endif

    `ifdef UDB_MXLEN_64
        fcvt_s_lu_rounding_op: coverpoint ins.current.insn {
            wildcard bins fcvt_s_lu = {FCVT_S_LU};
        }
        fcvt_s_lu_rounding_vals: coverpoint ins.current.rs1_val[63:0] {
            bins tie_even = {64'h0000010000010000};
            bins tie_odd = {64'h0000010000030000};
            bins quarter_ulp = {64'h0000020000010000};
        }
        cp_fcvt_s_lu_rounding: cross fcvt_s_lu_rounding_op, fcvt_s_lu_rounding_vals, static_rm;
    `endif

    `ifdef UDB_MXLEN_64
        `ifdef D_SUPPORTED
            fcvt_d_l_rounding_op: coverpoint ins.current.insn {
                wildcard bins fcvt_d_l = {FCVT_D_L};
            }
            fcvt_d_l_rounding_vals: coverpoint ins.current.rs1_val[63:0] {
                bins tie_pos = {64'h0020000000000001};
                bins tie_neg = {64'hFFDFFFFFFFFFFFFF};
                bins above_half = {64'h0040000000000003};
            }
            cp_fcvt_d_l_rounding: cross fcvt_d_l_rounding_op, fcvt_d_l_rounding_vals, static_rm;
        `endif
    `endif

    `ifdef UDB_MXLEN_64
        `ifdef D_SUPPORTED
            fcvt_d_lu_rounding_op: coverpoint ins.current.insn {
                wildcard bins fcvt_d_lu = {FCVT_D_LU};
            }
            fcvt_d_lu_rounding_vals: coverpoint ins.current.rs1_val[63:0] {
                bins tie_even = {64'h0020000000000001};
                bins tie_odd = {64'h0020000000000003};
                bins quarter_ulp = {64'h0040000000000001};
            }
            cp_fcvt_d_lu_rounding: cross fcvt_d_lu_rounding_op, fcvt_d_lu_rounding_vals, static_rm;
        `endif
    `endif

    `ifdef ZFH_SUPPORTED
        fcvt_h_w_rounding_op: coverpoint ins.current.insn {
            wildcard bins fcvt_h_w = {FCVT_H_W};
        }
        fcvt_h_w_rounding_vals: coverpoint ins.current.rs1_val[31:0] {
            bins tie_pos = {32'h00000801};
            bins tie_neg = {32'hFFFFF7FF};
            bins above_half = {32'h00001003};
            bins ovf_tie = {32'h0000FFF0};
            bins ovf_below_neg = {32'hFFFF0011};
        }
        cp_fcvt_h_w_rounding: cross fcvt_h_w_rounding_op, fcvt_h_w_rounding_vals, static_rm;
    `endif

    `ifdef ZFH_SUPPORTED
        fcvt_h_wu_rounding_op: coverpoint ins.current.insn {
            wildcard bins fcvt_h_wu = {FCVT_H_WU};
        }
        fcvt_h_wu_rounding_vals: coverpoint ins.current.rs1_val[31:0] {
            bins tie_even = {32'h00000801};
            bins tie_odd = {32'h00000803};
            bins quarter_ulp = {32'h00001001};
            bins ovf_tie = {32'h0000FFF0};
            bins ovf_below = {32'h0000FFEF};
        }
        cp_fcvt_h_wu_rounding: cross fcvt_h_wu_rounding_op, fcvt_h_wu_rounding_vals, static_rm;
    `endif

    `ifdef UDB_MXLEN_64
        `ifdef ZFH_SUPPORTED
            fcvt_h_l_rounding_op: coverpoint ins.current.insn {
                wildcard bins fcvt_h_l = {FCVT_H_L};
            }
            fcvt_h_l_rounding_vals: coverpoint ins.current.rs1_val[63:0] {
                bins tie_pos = {64'h0000000000000801};
                bins tie_neg = {64'hFFFFFFFFFFFFF7FF};
                bins above_half = {64'h0000000000001003};
            }
            cp_fcvt_h_l_rounding: cross fcvt_h_l_rounding_op, fcvt_h_l_rounding_vals, static_rm;
        `endif
    `endif

    `ifdef UDB_MXLEN_64
        `ifdef ZFH_SUPPORTED
            fcvt_h_lu_rounding_op: coverpoint ins.current.insn {
                wildcard bins fcvt_h_lu = {FCVT_H_LU};
            }
            fcvt_h_lu_rounding_vals: coverpoint ins.current.rs1_val[63:0] {
                bins tie_even = {64'h0000000000000801};
                bins tie_odd = {64'h0000000000000803};
                bins quarter_ulp = {64'h0000000000001001};
            }
            cp_fcvt_h_lu_rounding: cross fcvt_h_lu_rounding_op, fcvt_h_lu_rounding_vals, static_rm;
        `endif
    `endif

    `ifdef ZFA_SUPPORTED
        // fround and froundnx at halfway and fractional values under every static rounding mode
        fround_s_op: coverpoint ins.current.insn {
            wildcard bins fround = {FROUND_S};
            wildcard bins froundnx = {FROUNDNX_S};
        }
        fround_s_vals: coverpoint ins.current.fs1_val[31:0] {
            bins tie_pos = {32'h40200000};
            bins tie_neg = {32'hC0200000};
            bins above_half = {32'h4A000003};
            bins neg_half = {32'hBF000000};
        }
        cp_fround_s: cross fround_s_op, fround_s_vals, static_rm;
    `endif

    `ifdef ZFA_SUPPORTED
        `ifdef D_SUPPORTED
            fround_d_op: coverpoint ins.current.insn {
                wildcard bins fround = {FROUND_D};
                wildcard bins froundnx = {FROUNDNX_D};
            }
            fround_d_vals: coverpoint ins.current.fs1_val[63:0] {
                bins tie_pos = {64'h4004000000000000};
                bins tie_neg = {64'hC004000000000000};
                bins above_half = {64'h4310000000000003};
                bins neg_half = {64'hBFE0000000000000};
            }
            cp_fround_d: cross fround_d_op, fround_d_vals, static_rm;
        `endif
    `endif

    `ifdef ZFA_SUPPORTED
        `ifdef ZFH_SUPPORTED
            fround_h_op: coverpoint ins.current.insn {
                wildcard bins fround = {FROUND_H};
                wildcard bins froundnx = {FROUNDNX_H};
            }
            fround_h_vals: coverpoint ins.current.fs1_val[15:0] {
                bins tie_pos = {16'h4100};
                bins tie_neg = {16'hC100};
                bins above_half = {16'h5C03};
                bins neg_half = {16'hB800};
            }
            cp_fround_h: cross fround_h_op, fround_h_vals, static_rm;
        `endif
    `endif

    `ifdef ZFA_SUPPORTED
        `ifdef D_SUPPORTED
            // fcvtmod.w.d with out-of-range, inexact and non-finite inputs
            fcvtmod_w_d_op: coverpoint ins.current.insn {
                wildcard bins fcvtmod_w_d = {FCVTMOD_W_D};
            }
            fcvtmod_w_d_vals: coverpoint ins.current.fs1_val[63:0] {
                bins p2_31 = {64'h41E0000000000000};
                bins m2_31_m1 = {64'hC1E0000000200000};
                bins p2_31_mhalf = {64'h41DFFFFFFFE00000};
                bins m2_31_mhalf = {64'hC1E0000000100000};
                bins p2_32_p5 = {64'h41F0000000500000};
                bins m2_32_m5 = {64'hC1F0000000500000};
                bins p3_2_31_frac = {64'h41F8000000040000};
                bins big = {64'h4538000000000000};
                bins m0_75 = {64'hBFE8000000000000};
                bins pinf = {64'h7FF0000000000000};
                bins minf = {64'hFFF0000000000000};
                bins qnan = {64'h7FF8000000000000};
                bins snan = {64'h7FF0000000000001};
            }
            cp_fcvtmod_w_d: cross fcvtmod_w_d_op, fcvtmod_w_d_vals;
        `endif
    `endif
 endgroup

function void zicsrf_sample(int hart, int issue, ins_t ins);
    ZicsrF_cg.sample(ins);
endfunction
