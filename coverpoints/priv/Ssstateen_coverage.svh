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
        wildcard bins csrs = {CSRRS};
        wildcard bins csrc = {CSRRC};
    }
    sstateen_csrs: coverpoint ins.current.insn[31:20] {
        bins sstateen0 = {CSR_SSTATEEN0};
        bins sstateen1 = {CSR_SSTATEEN1};
        bins sstateen2 = {CSR_SSTATEEN2};
        bins sstateen3 = {CSR_SSTATEEN3};
    }

    // csrs sets the walking 1 and csrc clears the walking 0
    walk_ops: coverpoint ins.current.insn {
        wildcard bins csrs = {CSRRS};
        wildcard bins csrc = {CSRRC};
    }
    walk_bit: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b[] = {[0:`UDB_MXLEN-1]};
    }

    // Bit 63 (SE<n>) of the mstateen<n> matching the sstateen<n> being accessed; n is
    // the low two bits of the CSR address. On RV32 the bit is bit 31 of mstateen<n>h.
    `ifdef UDB_MXLEN_64
        mstateen_se_n_one: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0) + int'(ins.current.insn[21:20]), "mstateen", "mstateen")[63] {
            bins se_enabled = {1'b1};
        }
    `else
        mstateen_se_n_one: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0H) + int'(ins.current.insn[21:20]), "mstateenh", "mstateenh")[31] {
            bins se_enabled = {1'b1};
        }
    `endif

    // fcsr
    `ifdef ZFINX_SUPPORTED
        misa_F_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "misa", "exts")[5] {
            bins F_clear = {1'b0};
        }
        fcsr_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstateen0", "fcsr")[0] iff get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0", "fcsr")[0] == 1'b1 {
            bins fcsr_zero = {1'b0};
            bins fcsr_one  = {1'b1};
        }
        fcsr_csrs: coverpoint ins.current.insn[31:20] {
            wildcard bins frm    = {CSR_FRM};
            wildcard bins fflags = {CSR_FFLAGS};
            wildcard bins fcsr   = {CSR_FCSR};
        }
        fp_instrs: coverpoint ins.current.insn {
            wildcard bins fadd_s   = {FADD_S};
            wildcard bins fcvt_ws  = {FCVT_W_S};
            wildcard bins fcvt_sw  = {FCVT_S_W};
            wildcard bins fclass_s = {FCLASS_S};
        }
    `endif

    // jvt
    `ifdef ZCMT_SUPPORTED
        jvt_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstateen0", "jvt")[0] iff get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0", "jvt")[0] == 1'b1 {
            bins jvt_disabled = {1'b0};
            bins jvt_enabled  = {1'b1};
        }
        jvt_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins jvt = {CSR_JVT};
        }
    `endif

    cp_walking_ones:         cross priv_mode_s, sstateen_csrs, walk_ops, walk_bit, mstateen_se_n_one;
    cp_csr_illegal_accesses: cross priv_mode_u, sstateen_csrs, csrops, mstateen_se_n_one;

    `ifdef ZFINX_SUPPORTED
        cp_fcsr:     cross priv_mode_s_u, misa_F_clear, mstateen_se_n_one, fcsr_state, csrops, fcsr_csrs;
        cp_fcsr_fp_instrs: cross priv_mode_s_u, misa_F_clear, mstateen_se_n_one, fcsr_state, fp_instrs;
    `endif

    `ifdef ZCMT_SUPPORTED
        cp_jvt: cross priv_mode_s_u, mstateen_se_n_one, jvt_state, csrops, jvt_csr;
    `endif
endgroup

function void ssstateen_sample(int hart, int issue, ins_t ins);
    Ssstateen_cg.sample(ins);
endfunction
