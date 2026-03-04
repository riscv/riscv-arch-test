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
        wildcard bins csrrw = {32'b????????????_?????_001_?????_1110011};
    }
    csrop: coverpoint ins.current.insn[14:12] iff (ins.current.insn[6:0] == 7'b1110011) {
        bins csrrs = {3'b010};
        bins csrrc = {3'b011};
    }
    fcsr: coverpoint ins.current.insn[31:20] {
        bins fcsr = {12'h003};
    }
    frm: coverpoint ins.current.insn[31:20] {
        bins frm = {12'h002};
    }
    fflags: coverpoint ins.current.insn[31:20] {
        bins fflags = {12'h001};
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
        bins b_1[] = { [0:`XLEN-1] };
    }

    fadd: coverpoint ins.current.insn {
        wildcard bins fadd = {32'b00000_00_?????_?????_???_?????_1010011};
    }//                                 ^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ assumes single precision since there isn't a good
    //                                                                      way to specify the fs1 and fs2 values otherwise
    fsub: coverpoint ins.current.insn {
        wildcard bins fsub = {32'b00001_00_?????_?????_???_?????_1010011};
    }
    fdiv: coverpoint ins.current.insn {
        wildcard bins fdiv = {32'b00011_00_?????_?????_???_?????_1010011};
    }
    fmul: coverpoint ins.current.insn {
        wildcard bins fmul = {32'b00010_00_?????_?????_???_?????_1010011};
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
    cp_fflags_set_m_NV:       cross fsub,  fs1_infinity, fs2_infinity;
    cp_fflags_set_m_DZ:       cross fdiv,  fs1_one,      fs2_zero;
    cp_fflags_set_m_OF:       cross fadd,  fs1_largest,  fs2_largest;
    cp_fflags_set_m_UF:       cross fmul,  fs1_smallest, fs2_smallest;
    cp_fflags_set_m_NX:       cross fdiv,  fs1_one,      fs2_three;

    // very specific tests to check that underflow is computed after rounding
    // These come from Berkeley TestFloat cases that set underflow = 0 after rounding but 1 if done before rounding
    // single-precision (S) cases
    cp_underflow_after_rounding_fma_s_rdn: coverpoint ins.current.insn iff
        (ins.current.fs1_val[31:0] == 32'h3F00FBFF & ins.current.fs2_val[31:0] == 32'h80000001 & ins.current.fs3_val[31:0] == 32'h807FFFFF & ins.current.insn[14:12] == 3'b010) {
            wildcard bins fmadd = {FMADD_S};
        }

    cp_underflow_after_rounding_fmul_s_rup: coverpoint ins.current.insn iff
        (ins.current.fs1_val[31:0] == 32'h00800001 & ins.current.fs2_val[31:0] == 32'h3F7FFFFE & ins.current.insn[14:12] == 3'b011) {
            wildcard bins fmul = {FMUL_S};
        }

    `ifdef D_SUPPORTED
    // double-precision (D) cases
        cp_underflow_after_rounding_fma_d_rup: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'h802FFFFFFFBFFEFF & ins.current.fs2_val[63:0] == 64'h000FFFFFFFFFFFFE & ins.current.fs3_val[63:0] == 64'h0010000000000000  & ins.current.insn[14:12] == 3'b011) {
                wildcard bins fmadd = {FMADD_D};
            }

        cp_underflow_after_rounding_fmul_d_rdn: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'h0010000000000001 & ins.current.fs2_val[63:0] == 64'hBFEFFFFFFFFFFFFE & ins.current.insn[14:12] == 3'b010) {
                wildcard bins fmul = {FMUL_D};
            }

        cp_underflow_after_rounding_fcvt_s_d_rne: coverpoint ins.current.insn iff
            (ins.current.fs1_val[63:0] == 64'hB80FFFFFFFFDFEFF & ins.current.insn[14:12] == 3'b000) {
                wildcard bins fcvt = {FCVT_S_D};
            }
    `endif

    `ifdef Q_SUPPORTED
    // quad-precision (Q) cases
        cp_underflow_after_rounding_fma_q_rdn: coverpoint ins.current.insn iff
            (ins.current.fs1_val == 128'h3F9800000000000001FFFFFFFF7FFFFE & ins.current.fs2_val == 128'h00000000000000000000000000000001 & ins.current.fs3_val == 128'h80010000000000000000000000000000 & ins.current.insn[14:12] == 3'b010) {
                wildcard bins fmadd = {FMADD_Q};
            }

        cp_underflow_after_rounding_fmul_q_rne: coverpoint ins.current.insn iff
            (ins.current.fs1_val == 128'h0000FFFFFFFFFFFFFFFFFFFFFFFFFFFF & ins.current.fs2_val == 128'h3FFF0000000000000000000000000001 & ins.current.insn[14:12] == 3'b000) {
                wildcard bins fmul = {FMUL_Q};
            }

        cp_underflow_after_rounding_fcvt_s_q_rup: coverpoint ins.current.insn iff
            (ins.current.fs1_val == 128'h3F80FFFFFFFE0000000000FFFFFFFFFF & ins.current.insn[14:12] == 3'b011) {
                wildcard bins fcvt = {FCVT_S_Q};
            }
    `endif

    `ifdef ZFH_SUPPORTED
    // half-precision (H) cases
        cp_underflow_after_rounding_fma_h_rne: coverpoint ins.current.insn iff
            (ins.current.fs1_val[15:0] == 16'h0BC7 & ins.current.fs2_val[15:0] == 16'h03FF & ins.current.fs3_val[15:0] == 16'h8400 & ins.current.insn[14:12] == 3'b000) {
                wildcard bins fmadd = {FMADD_H};
            }

        cp_underflow_after_rounding_fmul_h_rup: coverpoint ins.current.insn iff
            (ins.current.fs1_val[15:0] == 16'h0401 & ins.current.fs2_val[15:0] == 16'h3BF8 & ins.current.insn[14:12] == 3'b011) {
                wildcard bins fmul = {FMUL_H};
            }

        cp_underflow_after_rounding_fcvt_h_s_rne: coverpoint ins.current.insn iff
            (ins.current.fs1_val[31:0] == 32'h387FF000 & ins.current.insn[14:12] == 3'b000) {
                wildcard bins fcvt = {FCVT_H_S};
            }
    `else
        `ifdef ZFHMIN_SUPPORTED
            // same test case, repeated if only Zfhmin is supported
            cp_underflow_after_rounding_fcvt_h_s_rne: coverpoint ins.current.insn iff
                (ins.current.fs1_val[31:0] == 32'h387FF000 & ins.current.insn[14:12] == 3'b000) {
                    wildcard bins fcvt = {FCVT_H_S};
                }
        `endif
   `endif
 endgroup

function void zicsrf_sample(int hart, int issue, ins_t ins);
    ZicsrF_cg.sample(ins);
endfunction
