///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////
`define COVER_SSSTATEEN
`include "general/RISCV_coverage_stateen.svh"
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

    // Modes that access the state: S (HS with H) and U, and VS and VU with H. hstateen0 only affects VS and
    // VU, so the S and U accesses check that it does not change them.
    priv_mode_s_u_vs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
            bins S_mode = {3'b001};
            bins U_mode = {3'b000};
        `ifdef H_SUPPORTED
            bins VS_mode = {3'b101};
            bins VU_mode = {3'b100};
        `endif
    }

    // SE<n> of mstateen<n>, for the CSR with address bits [21:20] = n. The sstateen<n> and hstateen<n>
    // CSRs are accessible only when it is set.
    mstateen_se_n_one: coverpoint mstateen_se_n(ins) {
        bins se_enabled = {1'b1};
    }

    // fcsr
    `ifdef ZFINX_SUPPORTED
        misa_F_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "misa", "exts")[5] {
            bins F_clear = {1'b0};
        }
        fcsr_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", 0), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr", 0), sstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "fcsr")} {
            `ifdef H_SUPPORTED
                bins h_s[] = {[3'b100:3'b111]};
            `else
                bins h_s[] = {3'b110, 3'b111};
            `endif
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
        jvt_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "jvt", 0), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "jvt", 0), sstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "jvt")} {
            `ifdef H_SUPPORTED
                bins h_s[] = {[3'b100:3'b111]};
            `else
                bins h_s[] = {3'b110, 3'b111};
            `endif
        }
        jvt_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins jvt = {CSR_JVT};
        }
    `endif

    // hstateen CSRs and the state they gate from VS and VU-mode
    `ifdef H_SUPPORTED
        hstateen_csrs: coverpoint ins.current.insn[31:20] {
            bins hstateen0 = {CSR_HSTATEEN0};
            bins hstateen1 = {CSR_HSTATEEN1};
            bins hstateen2 = {CSR_HSTATEEN2};
            bins hstateen3 = {CSR_HSTATEEN3};
            `ifdef UDB_MXLEN_32
                bins hstateen0h = {CSR_HSTATEEN0H};
                bins hstateen1h = {CSR_HSTATEEN1H};
                bins hstateen2h = {CSR_HSTATEEN2H};
                bins hstateen3h = {CSR_HSTATEEN3H};
            `endif
        }
        sstateen0_csr: coverpoint ins.current.insn[31:20] {
            bins sstateen0 = {CSR_SSTATEEN0};
        }
        // SE<n> of mstateen<n> and hstateen<n> for the sstateen<n> being accessed
        se_state: coverpoint {mstateen_se_n(ins), hstateen_se_n(ins)} {
            bins se_h0 = {2'b10};
            bins se_h1 = {2'b11};
        }

        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            hstateen_envcfg_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "envcfg", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "envcfg", 1)} {
                bins h[] = {[2'b10:2'b11]};
            }
            senvcfg_csr: coverpoint ins.current.insn[31:20] {
                bins senvcfg = {CSR_SENVCFG};
            }
        `endif

        `ifdef UDB_SCONTEXT_IMPLEMENTED
            hstateen_context_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "context", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "context", 1)} {
                bins h[] = {[2'b10:2'b11]};
            }
            scontext_csr: coverpoint ins.current.insn[31:20] {
                wildcard bins scontext = {CSR_SCONTEXT};
            }
        `endif

        `ifdef SSAIA_SUPPORTED
            hstateen_imsic_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "imsic", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "imsic", 1)} {
                bins h[] = {[2'b10:2'b11]};
            }
            imsic_csrs: coverpoint ins.current.insn[31:20] {
                wildcard bins stopei = {CSR_STOPEI};
            }
            hstateen_aia_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "aia", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "aia", 1)} {
                bins h[] = {[2'b10:2'b11]};
            }
            aia_csrs: coverpoint ins.current.insn[31:20] {
                bins stopi = {CSR_STOPI};
                `ifdef UDB_MXLEN_32
                    bins sieh = {CSR_SIEH};
                    bins siph = {CSR_SIPH};
                `endif
            }
        `endif

        `ifdef SSCSRIND_SUPPORTED
            hstateen_csrind_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "csrind", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "csrind", 1)} {
                bins h[] = {[2'b10:2'b11]};
            }
            csrind_csrs: coverpoint ins.current.insn[31:20] {
                bins siselect = {CSR_SISELECT};
                bins sireg    = {CSR_SIREG};
                bins sireg2   = {CSR_SIREG2};
                bins sireg3   = {CSR_SIREG3};
                bins sireg4   = {CSR_SIREG4};
                bins sireg5   = {CSR_SIREG5};
                bins sireg6   = {CSR_SIREG6};
            }
        `endif

        `ifdef SSCTR_SUPPORTED
            hstateen_ctr_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "ctr", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "ctr", 1)} {
                bins h[] = {[2'b10:2'b11]};
            }
            ctr_csrs: coverpoint ins.current.insn[31:20] {
                wildcard bins sctrdepth  = {CSR_SCTRDEPTH};
                wildcard bins sctrstatus = {CSR_SCTRSTATUS};
            }
        `endif
    `endif

    cp_walking_ones: cross priv_mode_s, sstateen_csrs, walk_ops, walk_bit, mstateen_se_n_one;
    cp_csr_illegal_accesses: cross priv_mode_u_maybevu, sstateen_csrs, csrops, mstateen_se_n_one;

    `ifdef ZFINX_SUPPORTED
        cp_fcsr: cross priv_mode_s_u_vs_vu, misa_F_clear, fcsr_state, csrops, fcsr_csrs;
        cp_fcsr_fp_instrs: cross priv_mode_s_u_vs_vu, misa_F_clear, fcsr_state, fp_instrs;
    `endif

    `ifdef ZCMT_SUPPORTED
        cp_jvt: cross priv_mode_s_u_vs_vu, jvt_state, csrops, jvt_csr;
    `endif

    `ifdef H_SUPPORTED
        cp_hstateen_walking_ones:     cross priv_mode_s, hstateen_csrs, walk_ops, walk_bit, mstateen_se_n_one;
        cp_hstateen_illegal_accesses: cross priv_mode_vs_u_vu, hstateen_csrs, csrops, mstateen_se_n_one;
        cp_hstateen_se_controls_sstateen:   cross priv_mode_s_maybevs, se_state, csrops, sstateen_csrs;

        `ifdef SM1P12P0_OR_LATER_SUPPORTED
            cp_hstateen_envcfg: cross csrops, priv_mode_s_u_vs_vu, senvcfg_csr, hstateen_envcfg_state;
        `endif
        `ifdef UDB_SCONTEXT_IMPLEMENTED
            cp_hstateen_context: cross csrops, priv_mode_s_u_vs_vu, scontext_csr, hstateen_context_state;
        `endif
        `ifdef SSAIA_SUPPORTED
            cp_hstateen_imsic: cross csrops, priv_mode_s_u_vs_vu, imsic_csrs, hstateen_imsic_state;
            cp_hstateen_aia:   cross csrops, priv_mode_s_u_vs_vu, aia_csrs, hstateen_aia_state;
        `endif
        `ifdef SSCSRIND_SUPPORTED
            cp_hstateen_csrind: cross csrops, priv_mode_s_u_vs_vu, csrind_csrs, hstateen_csrind_state;
        `endif
        `ifdef SSCTR_SUPPORTED
            cp_hstateen_ctr: cross csrops, priv_mode_s_u_vs_vu, ctr_csrs, hstateen_ctr_state;
        `endif
    `endif
endgroup

function void ssstateen_sample(int hart, int issue, ins_t ins);
    Ssstateen_cg.sample(ins);
endfunction
