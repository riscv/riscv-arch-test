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
    cp_frm_reserved_static_rm: cross fadd, frm_reserved, static_rm iff (ins.trap == 0);

    // very specific tests to check that underflow is computed after rounding
    // The operand sets come from Berkeley TestFloat cases whose exact result is tiny before rounding.
    // Each is crossed with every static rounding mode: in some modes the result is not tiny after
    // rounding (UF = 0), in others it is tiny after rounding even though the delivered result is +/-2^emin (UF = 1).
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

        underflow_fcvt_h_s: coverpoint ins.current.insn iff
            (ins.current.fs1_val[31:0] == 32'h387FF000) {
                wildcard bins fcvt = {FCVT_H_S};
            }
        cp_underflow_after_rounding_fcvt_h_s: cross underflow_fcvt_h_s, static_rm;
    `else
        `ifdef ZFHMIN_SUPPORTED
            // same test case, repeated if only Zfhmin is supported
            underflow_fcvt_h_s: coverpoint ins.current.insn iff
                (ins.current.fs1_val[31:0] == 32'h387FF000) {
                    wildcard bins fcvt = {FCVT_H_S};
                }
            cp_underflow_after_rounding_fcvt_h_s: cross underflow_fcvt_h_s, static_rm;
        `endif
   `endif
 endgroup

function void zicsrf_sample(int hart, int issue, ins_t ins);
    ZicsrF_cg.sample(ins);
endfunction
