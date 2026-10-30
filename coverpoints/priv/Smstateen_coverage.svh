///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
// Written by : Ayesha Anwar ayesha.anwaar2005@gmail.com
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SMSTATEEN
`include "general/RISCV_coverage_stateen.svh"
covergroup Smstateen_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrops: coverpoint ins.current.insn {
        wildcard bins csrw = {CSRRW};
        wildcard bins csrs = {CSRRS};
        wildcard bins csrc = {CSRRC};
    }
    priv_mode_all_sup: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
            bins M_mode = {3'b011};
            bins U_mode = {3'b000};
        `ifdef S_SUPPORTED
            bins S_mode = {3'b001};
        `endif
        `ifdef H_SUPPORTED
            bins VS_mode = {3'b101};
            bins VU_mode = {3'b100};
        `endif
    }
    priv_mode_all_sup_no_m: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
            bins U_mode = {3'b000};
        `ifdef S_SUPPORTED
            bins S_mode = {3'b001};
        `endif
        `ifdef H_SUPPORTED
            bins VS_mode = {3'b101};
            bins VU_mode = {3'b100};
        `endif
    }

    mstateen_csrs: coverpoint ins.current.insn[31:20] {
        bins mstateen0 = {CSR_MSTATEEN0};
        bins mstateen1 = {CSR_MSTATEEN1};
        bins mstateen2 = {CSR_MSTATEEN2};
        bins mstateen3 = {CSR_MSTATEEN3};
        `ifdef UDB_MXLEN_32
            bins mstateen0h = {CSR_MSTATEEN0H};
            bins mstateen1h = {CSR_MSTATEEN1H};
            bins mstateen2h = {CSR_MSTATEEN2H};
            bins mstateen3h = {CSR_MSTATEEN3H};
        `endif
    }

    // csrs sets the walking 1 and csrc clears the walking 0
    walk_ops: coverpoint ins.current.insn {
        wildcard bins csrs = {CSRRS};
        wildcard bins csrc = {CSRRC};
    }
    walk_bit: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b[] = {[0:`UDB_MXLEN-1]};
    }

    // Feature state. Each state coverpoint samples the control bit in mstateen0 and in the lower-level
    // CSRs that hold it (hstateen0 with H, sstateen0 with S). A clear mstateen0 bit makes the other bits
    // read-only zero, so they are not sampled for that state. A set bit is tested with the lower-level
    // bits set, so only mstateen0 changes the result. The lower-level bits are varied in Ssstateen.

    // imsic and aia
    `ifdef SSAIA_SUPPORTED
        imsic_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "imsic", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "imsic", 1)} {
            wildcard bins imsic_disabled = {2'b0?};
            bins imsic_enabled  = {2'b11};
        }
        imsic_csrs: coverpoint ins.current.insn[31:20] {
            wildcard bins stopei = {CSR_STOPEI};
            `ifdef H_SUPPORTED
              wildcard bins vstopei = {CSR_VSTOPEI};
            `endif
        }
        aia_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "aia", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "aia", 1)} {
            wildcard bins aia_disabled = {2'b0?};
            bins aia_enabled  = {2'b11};
        }
        // Ssaia state gated by mstateen0.AIA and not by CSRIND or IMSIC
        aia_csrs: coverpoint ins.current.insn[31:20] {
            bins stopi = {CSR_STOPI};
            `ifdef UDB_MXLEN_32
                bins sieh = {CSR_SIEH};
                bins siph = {CSR_SIPH};
            `endif
        }
    `endif

    // csrind
    `ifdef SSCSRIND_SUPPORTED
        csrind_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "csrind", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "csrind", 1)} {
            wildcard bins csrind_disabled = {2'b0?};
            bins csrind_enabled  = {2'b11};
        }
        csrind_csrs: coverpoint ins.current.insn[31:20] {
            bins siselect = {CSR_SISELECT};
            bins sireg    = {CSR_SIREG};
            bins sireg2   = {CSR_SIREG2};
            bins sireg3   = {CSR_SIREG3};
            bins sireg4   = {CSR_SIREG4};
            bins sireg5   = {CSR_SIREG5};
            bins sireg6   = {CSR_SIREG6};
            `ifdef H_SUPPORTED
                bins vsiselect = {CSR_VSISELECT};
                bins vsireg    = {CSR_VSIREG};
                bins vsireg2   = {CSR_VSIREG2};
                bins vsireg3   = {CSR_VSIREG3};
                bins vsireg4   = {CSR_VSIREG4};
                bins vsireg5   = {CSR_VSIREG5};
                bins vsireg6   = {CSR_VSIREG6};
            `endif
        }
    `endif

    // fcsr
    `ifdef ZFINX_SUPPORTED
        misa_F_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "misa", "exts")[5] {
            bins F_clear = {1'b0};
        }
        fcsr_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "fcsr", 0), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "fcsr", 0), sstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "fcsr")} {
            wildcard bins fcsr_disabled = {3'b0??};
            bins fcsr_enabled  = {3'b111};
        }
        fscr_csrs: coverpoint ins.current.insn[31:20] {
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

    // envcfg
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        envcfg_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "envcfg", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "envcfg", 1)} {
            wildcard bins envcfg_disabled = {2'b0?};
            bins envcfg_enabled  = {2'b11};
        }
        envcfg_csrs: coverpoint ins.current.insn[31:20] {
            bins senvcfg = {CSR_SENVCFG};
            `ifdef H_SUPPORTED
                bins henvcfg = {CSR_HENVCFG};
                `ifdef UDB_MXLEN_32
                    bins henvcfgh = {CSR_HENVCFGH};
                `endif
            `endif
        }
    `endif

    // jvt
    `ifdef ZCMT_SUPPORTED
        jvt_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "jvt", 0), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "jvt", 0), sstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "jvt")} {
            wildcard bins jvt_disabled = {3'b0??};
            bins jvt_enabled  = {3'b111};
        }
        jvt_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins jvt = {CSR_JVT};
        }
    `endif

    // context
    `ifdef UDB_SCONTEXT_IMPLEMENTED
      `define CONTEXT_SUPPORTED
    `endif
    `ifdef UDB_HCONTEXT_IMPLEMENTED
      `ifndef CONTEXT_SUPPORTED
        `define CONTEXT_SUPPORTED
      `endif
    `endif
    `ifdef CONTEXT_SUPPORTED
        context_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "context", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "context", 1)} {
            wildcard bins context_disabled = {2'b0?};
            bins context_enabled  = {2'b11};
        }
        context_csrs: coverpoint ins.current.insn[31:20] {
            `ifdef UDB_SCONTEXT_IMPLEMENTED
                bins scontext = {CSR_SCONTEXT};
            `endif
            `ifdef UDB_HCONTEXT_IMPLEMENTED
                bins hcontext = {CSR_HCONTEXT};
            `endif
        }
    `endif

    // p1p13
  `ifdef SM1P13P0_OR_LATER_SUPPORTED
      // mstateen0.P1P13 only controls hedelegh, the high half of hedeleg, which exists only on RV32
      // with the hypervisor extension; anywhere else the bit is read-only zero.
      `ifdef H_SUPPORTED
      `ifdef UDB_MXLEN_32
          p1p13_state: coverpoint mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "p1p13", 1) {
              bins p1p13_disabled = {1'b0};
              bins p1p13_enabled  = {1'b1};
          }
          hedelegh_csr: coverpoint ins.current.insn[31:20] {
              wildcard bins hedelegh = {CSR_HEDELEGH};
          }
      `endif
      `endif
  `endif

    // srmcfg
    `ifdef SSQOSID_SUPPORTED
        srmcfg_state: coverpoint mstateen0_bit(ins.hart, ins.issue, `SAMPLE_AFTER, "srmcfg", 1) {
            bins srmcfg_disabled = {1'b0};
            bins srmcfg_enabled  = {1'b1};
        }
        srmcfg_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins srmcfg = {CSR_SRMCFG};
        }
    `endif

    // ctr
    `ifdef SSCTR_SUPPORTED
        ctr_state: coverpoint {mstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "ctr", 1), hstateen0_bit(ins.hart, ins.issue, `SAMPLE_CURRENT, "ctr", 1)} {
            wildcard bins ctr_disabled = {2'b0?};
            bins ctr_enabled  = {2'b11};
        }
        ctr_csrs: coverpoint ins.current.insn[31:20] {
            wildcard bins sctrdepth  = {CSR_SCTRDEPTH};
            wildcard bins sctrstatus = {CSR_SCTRSTATUS};
        }
    `endif

    `ifdef S_SUPPORTED
        sstateen0_csr: coverpoint ins.current.insn[31:20] {
                bins sstateen0 = {CSR_SSTATEEN0};
        }
        sstateen_csrs: coverpoint ins.current.insn[31:20] {
                bins sstateen0 = {CSR_SSTATEEN0};
                bins sstateen1 = {CSR_SSTATEEN1};
                bins sstateen2 = {CSR_SSTATEEN2};
                bins sstateen3 = {CSR_SSTATEEN3};
        }
        // SE<n> of mstateen<n> and of hstateen<n> for the sstateen<n> being accessed. A clear mstateen<n>
        // bit makes the hstateen<n> bit read-only zero. A set bit is tested with hstateen<n> set, and
        // hstateen<n> is varied in Ssstateen.
        mstateen_se: coverpoint mstateen_se_n(ins) {
        }
        se_state: coverpoint {mstateen_se_n(ins), hstateen_se_n(ins)} {
            wildcard bins se_disabled = {2'b0?};
            bins se_enabled  = {2'b11};
        }
        // mstateen0 has only SE0 set, so every other bit of sstateen0 must be read-only zero
        `ifdef UDB_MXLEN_64
            mstateen0_se0_only: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0", "mstateen0") {
                bins se0_only = {64'h8000_0000_0000_0000};
            }
        `else
            mstateen0_se0_only: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0h", "mstateen0h"),
                                            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0", "mstateen0")} {
                bins se0_only = {64'h8000_0000_0000_0000};
            }
        `endif
    `endif

    // hstateen0-3 are accessible from HS-mode only when SE<n> of mstateen<n> is set
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
        hstateen0_csr: coverpoint ins.current.insn[31:20] {
            bins hstateen0 = {CSR_HSTATEEN0};
        }
    `endif

    cp_walking_ones: cross priv_mode_m, mstateen_csrs, walk_ops, walk_bit;
    cp_csr_illegal_accesses: cross priv_mode_all_sup_no_m, mstateen_csrs, csrops;

    `ifdef S_SUPPORTED
        cp_mstateen_se_controls_sstateen:  cross priv_mode_s_maybevs, se_state, csrops, sstateen_csrs;
        cp_mstateen0_se0_only_sstateen0:   cross priv_mode_m_s, mstateen0_se0_only, walk_ops, walk_bit, sstateen0_csr;
        `ifdef H_SUPPORTED
            cp_mstateen_se_controls_hstateen:     cross priv_mode_s, mstateen_se, csrops, hstateen_csrs;
            cp_mstateen0_se0_only_hstateen0:      cross priv_mode_m_s, mstateen0_se0_only, walk_ops, walk_bit, hstateen0_csr;
        `endif
    `endif

    `ifdef ZFINX_SUPPORTED
        cp_fcsr: cross misa_F_clear, priv_mode_all_sup, fcsr_state, csrops, fscr_csrs;
        cp_fcsr_fp_instrs: cross misa_F_clear, priv_mode_all_sup, fcsr_state, fp_instrs;
    `endif

    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        cp_envcfg: cross csrops, priv_mode_all_sup, envcfg_csrs, envcfg_state;
    `endif

    `ifdef ZCMT_SUPPORTED
        cp_jvt_access:     cross priv_mode_all_sup, csrops, jvt_csr, jvt_state;
    `endif

    `ifdef SDTRIG_SUPPORTED
        cp_context: cross csrops, context_csrs, context_state, priv_mode_all_sup;
    `endif

    `ifdef SM1P13P0_OR_LATER_SUPPORTED
    `ifdef H_SUPPORTED
    `ifdef UDB_MXLEN_32
        cp_p1p13: cross csrops, p1p13_state, hedelegh_csr, priv_mode_all_sup;
    `endif
    `endif
    `endif

    `ifdef SSQOSID_SUPPORTED
        cp_srmcfg: cross csrops, srmcfg_csr, srmcfg_state, priv_mode_all_sup;
    `endif

    `ifdef SSCTR_SUPPORTED
        cp_ctr: cross csrops, ctr_csrs, ctr_state, priv_mode_all_sup;
    `endif

    `ifdef SSCSRIND_SUPPORTED
        cp_csrind: cross csrops, csrind_csrs, csrind_state, priv_mode_all_sup;
    `endif

    `ifdef SSAIA_SUPPORTED
        cp_imsic: cross csrops, imsic_csrs, imsic_state, priv_mode_all_sup;
        cp_aia: cross csrops, aia_csrs, aia_state, priv_mode_all_sup;
    `endif

endgroup

function void smstateen_sample(int hart, int issue, ins_t ins);
    Smstateen_cg.sample(ins);
endfunction
