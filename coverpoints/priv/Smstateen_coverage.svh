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
covergroup Smstateen_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrops: coverpoint ins.current.insn {
        wildcard bins csrw = {CSRRW};
        wildcard bins csrs = {CSRRS};
        wildcard bins csrc = {CSRRC};
    }
    priv_mode_m_maybes_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
            bins M_mode = {3'b011};
            bins U_mode = {3'b000};
        `ifdef S_SUPPORTED
            bins S_mode = {3'b001};
        `endif
    }
    priv_mode_maybes_u: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
            bins U_mode = {3'b000};
        `ifdef S_SUPPORTED
            bins S_mode = {3'b001};
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

    // imsic and aia
    `ifdef SSAIA_SUPPORTED
        `ifdef UDB_MXLEN_64
            imsic_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "imsic") {
                bins imsic_disabled = {1'b0};
                bins imsic_enabled  = {1'b1};
            }
        `else
            imsic_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0h", "imsic") {
                bins imsic_disabled = {1'b0};
                bins imsic_enabled  = {1'b1};
            }
        `endif
        imsic_csrs: coverpoint ins.current.insn[31:20] {
            wildcard bins stopei = {CSR_STOPEI};
            wildcard bins vstopei = {CSR_VSTOPEI};
        }
        `ifdef UDB_MXLEN_64
            aia_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "aia") {
                bins aia_disabled = {1'b0};
                bins aia_enabled  = {1'b1};
            }
        `else
            aia_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0h", "aia") {
                bins aia_disabled = {1'b0};
                bins aia_enabled  = {1'b1};
            }
        `endif
        // Ssaia state gated by mstateen0.AIA and not by CSRIND or IMSIC
        aia_csrs: coverpoint ins.current.insn[31:20] {
            bins stopi = {CSR_STOPI};
            `ifdef UDB_MXLEN_32
                bins sieh = {CSR_SIEH};
                bins siph = {CSR_SIPH};
            `endif
        }
    `endif

    // fcsr
    `ifdef ZFINX_SUPPORTED
        misa_F_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "misa", "exts")[5] {
            bins F_clear = {1'b0};
        }
        fcsr_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "fcsr") {
            bins fcsr_zero = {1'b0};
            bins fcsr_one  = {1'b1};
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
      `ifdef UDB_MXLEN_64
          envcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0", "envcfg")[0] {
              bins envcfg_disabled = {1'b0};
              bins envcfg_enabled  = {1'b1};
          }
      `else
          envcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0h", "envcfg")[0] {
              bins envcfg_disabled = {1'b0};
              bins envcfg_enabled  = {1'b1};
          }
      `endif
      senvcfg_csr: coverpoint ins.current.insn[31:20] {
          bins senvcfg = {CSR_SENVCFG};
      }
    `endif

    // jvt
    `ifdef ZCMT_SUPPORTED
        jvt_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "jvt") {
            bins jvt_disabled = {1'b0};
            bins jvt_enabled  = {1'b1};
        }
        jvt_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins jvt = {CSR_JVT};
        }
    `endif

    // context
    `ifdef UDB_SCONTEXT_IMPLEMENTED
        `ifdef UDB_MXLEN_64
            context_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "context") {
                bins context_disabled = {1'b0};
                bins context_enabled  = {1'b1};
            }
        `else
            context_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0h", "context") {
                bins context_disabled = {1'b0};
                bins context_enabled  = {1'b1};
            }
        `endif
        scontext_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins scontext = {CSR_SCONTEXT};
        }
    `endif

    // p1p13 TODO: Move to Smstateen_H
  `ifdef SM1P13P0_OR_LATER_SUPPORTED
      // mstateen0.P1P13 only controls hedelegh, the high half of hedeleg, which exists only on RV32
      // with the hypervisor extension; anywhere else the bit is read-only zero.
      `ifdef H_SUPPORTED
      `ifdef UDB_MXLEN_32
          p1p13_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0h", "p1p13") {
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
        `ifdef UDB_MXLEN_64
            srmcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0", "srmcfg")[0] {
                bins srmcfg_disabled = {1'b0};
                bins srmcfg_enabled  = {1'b1};
            }
        `else
            srmcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0h", "srmcfg")[0] {
                bins srmcfg_disabled = {1'b0};
                bins srmcfg_enabled  = {1'b1};
            }
        `endif
        srmcfg_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins srmcfg = {CSR_SRMCFG};
        }
    `endif

    // ctr
    `ifdef SSCTR_SUPPORTED
        `ifdef UDB_MXLEN_64
            ctr_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "ctr") {
                bins ctr_disabled = {1'b0};
                bins ctr_enabled  = {1'b1};
            }
        `else
            ctr_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0h", "ctr") {
                bins ctr_disabled = {1'b0};
                bins ctr_enabled  = {1'b1};
            }
        `endif
        ctr_csrs: coverpoint ins.current.insn[31:20] {
            wildcard bins sctrdepth  = {CSR_SCTRDEPTH};
            wildcard bins sctrstatus = {CSR_SCTRSTATUS};
        }
    `endif

    `ifdef S_SUPPORTED
        sstateen0_csr: coverpoint ins.current.insn[31:20] {
                bins sstateen0 = {CSR_SSTATEEN0};
        }
        sstateen123_csrs: coverpoint ins.current.insn[31:20] {
                bins sstateen1 = {CSR_SSTATEEN1};
                bins sstateen2 = {CSR_SSTATEEN2};
                bins sstateen3 = {CSR_SSTATEEN3};
        }
        // Bit 63 (SE<n>) of the mstateen<n> matching the sstateen<n> being accessed; n is
        // the low two bits of the CSR address. On RV32 the bit is bit 31 of mstateen<n>h.
        `ifdef UDB_MXLEN_64
            mstateen_se_n: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0) + int'(ins.current.insn[21:20]), "mstateen", "mstateen")[63] {
            }
        `else
            mstateen_se_n: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0H) + int'(ins.current.insn[21:20]), "mstateenh", "mstateenh")[31] {
            }
        `endif
        // mstateen0 has only SE0 set, so every other bit of sstateen0 must be read-only zero
        `ifdef UDB_MXLEN_64
            mstateen0_se0_only: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0", "mstateen") {
                bins se0_only = {64'h8000_0000_0000_0000};
            }
        `else
            mstateen0_se0_only: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0H), "mstateenh", "mstateenh")
                    iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0", "mstateen") == 0) {
                bins se0_only = {32'h8000_0000};
            }
        `endif
    `endif

    cp_walking_ones: cross priv_mode_m, mstateen_csrs, walk_ops, walk_bit;
    cp_csr_illegal_accesses: cross priv_mode_maybes_u, mstateen_csrs, csrops;

    `ifdef S_SUPPORTED
        cp_mstateen0_se0_controls_sstateen0: cross priv_mode_s, mstateen_se_n, csrops, sstateen0_csr;
        cp_mstateen_se_controls_sstateen123: cross priv_mode_s, mstateen_se_n, csrops, sstateen123_csrs;
        cp_mstateen0_se0_only_sstateen0:      cross priv_mode_m_s, mstateen0_se0_only, walk_ops, walk_bit, sstateen0_csr;
    `endif

    `ifdef ZFINX_SUPPORTED
        cp_fcsr: cross misa_F_clear, priv_mode_m_maybes_u, fcsr_state, csrops, fscr_csrs;
        cp_fcsr_fp_instrs: cross misa_F_clear, priv_mode_m_maybes_u, fcsr_state, fp_instrs;
    `endif

    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        cp_envcfg: cross csrops, priv_mode_m_maybes_u, senvcfg_csr, envcfg_state;
    `endif

    `ifdef ZCMT_SUPPORTED
        cp_jvt_access:     cross priv_mode_maybes_u, csrops, jvt_csr, jvt_state;
    `endif

    `ifdef SDTRIG_SUPPORTED
        cp_context: cross csrops, scontext_csr, context_state, priv_mode_m_maybes_u;
    `endif

    `ifdef SM1P13P0_OR_LATER_SUPPORTED
    `ifdef H_SUPPORTED
    `ifdef UDB_MXLEN_32
        cp_p1p13: cross csrops, p1p13_state, hedelegh_csr, priv_mode_m_maybes_u;
    `endif
    `endif
    `endif

    `ifdef SSQOSID_SUPPORTED
        cp_srmcfg: cross csrops, srmcfg_csr, srmcfg_state, priv_mode_m_maybes_u;
    `endif

    `ifdef SSCTR_SUPPORTED
        cp_ctr: cross csrops, ctr_csrs, ctr_state, priv_mode_m_maybes_u;
    `endif

    `ifdef SSAIA_SUPPORTED
        cp_imsic: cross csrops, imsic_csrs, imsic_state, priv_mode_m_maybes_u;
        cp_aia: cross csrops, aia_csrs, aia_state, priv_mode_m_maybes_u;
    `endif

endgroup

function void smstateen_sample(int hart, int issue, ins_t ins);
    Smstateen_cg.sample(ins);
endfunction
