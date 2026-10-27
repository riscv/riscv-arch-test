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

    // ── Comprehensive CSR operation coverpoint ────────────────────────────
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

    // ── CSR address coverpoint — all mstateen CSRs ────────────────────────
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
    mstateen_walk_csrs: coverpoint ins.current.insn[31:20] {
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

    // ── Walking ones/zeros coverpoint ─────────────────────────────────────
    `ifdef UDB_MXLEN_64
        csr_walk: coverpoint ins.current.rs1_val {
            `ifdef ZFINX_SUPPORTED
                wildcard bins walking1_1  = {64'b??????????????????????????????????????????????????????????????1?};
            `endif
            `ifdef ZCMT_SUPPORTED
                wildcard bins walking1_2  = {64'b?????????????????????????????????????????????????????????????1??};
            `endif
            `ifdef SSCTR_SUPPORTED
                wildcard bins walking1_54  = {64'b?????????1??????????????????????????????????????????????????????};
            `endif
            `ifdef SSQOSID_SUPPORTED
                wildcard bins walking1_55  = {64'b????????1???????????????????????????????????????????????????????};
            `endif
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                wildcard bins walking1_56  = {64'b???????1????????????????????????????????????????????????????????};
            `endif
            `ifdef SDTRIG_SUPPORTED
                wildcard bins walking1_57 = {64'b??????1?????????????????????????????????????????????????????????};
            `endif
            `ifdef SSAIA_SUPPORTED
                wildcard bins walking1_58     = {64'b?????1??????????????????????????????????????????????????????????};
                wildcard bins walking1_59     = {64'b????1???????????????????????????????????????????????????????????};
            `endif
            `ifdef SSCSRIND_SUPPORTED
                wildcard bins walking1_60     = {64'b???1????????????????????????????????????????????????????????????};
            `endif
            wildcard bins walking1_62 = {64'b?1??????????????????????????????????????????????????????????????};
            wildcard bins walking1_63 = {64'b1???????????????????????????????????????????????????????????????};

            wildcard bins walking0_0  = {64'b???????????????????????????????????????????????????????????????0};
            wildcard bins walking0_1  = {64'b??????????????????????????????????????????????????????????????0?};
            wildcard bins walking0_2  = {64'b?????????????????????????????????????????????????????????????0??};
            wildcard bins walking0_54 = {64'b?????????0??????????????????????????????????????????????????????};
            wildcard bins walking0_55 = {64'b????????0???????????????????????????????????????????????????????};
            wildcard bins walking0_56 = {64'b???????0????????????????????????????????????????????????????????};
            wildcard bins walking0_57 = {64'b??????0?????????????????????????????????????????????????????????};
            wildcard bins walking0_58 = {64'b?????0??????????????????????????????????????????????????????????};
            wildcard bins walking0_59 = {64'b????0???????????????????????????????????????????????????????????};
            wildcard bins walking0_60 = {64'b???0????????????????????????????????????????????????????????????};
            wildcard bins walking0_61 = {64'b??0?????????????????????????????????????????????????????????????};
            wildcard bins walking0_62 = {64'b?0??????????????????????????????????????????????????????????????};
            wildcard bins walking0_63 = {64'b0???????????????????????????????????????????????????????????????};
        }
    `else
        csr_walk: coverpoint ins.current.rs1_val {
            `ifdef ZFINX_SUPPORTED
                wildcard bins walking1_1  = {32'b??????????????????????????????1?};
            `endif
            `ifdef ZCMT_SUPPORTED
                wildcard bins walking1_2  = {32'b?????????????????????????????1??};
            `endif
            `ifdef SSCTR_SUPPORTED
                wildcard bins walking1_22 = {32'b?????????1??????????????????????};
            `endif
            `ifdef SSQOSID_SUPPORTED
                wildcard bins walking1_23 = {32'b????????1???????????????????????};
            `endif
            `ifdef SM1P13P0_OR_LATER_SUPPORTED
                wildcard bins walking1_24 = {32'b???????1????????????????????????};
            `endif
            `ifdef SDTRIG_SUPPORTED
                wildcard bins walking1_25 = {32'b??????1?????????????????????????};
            `endif
            `ifdef SSAIA_SUPPORTED
                wildcard bins walking1_26 = {32'b?????1??????????????????????????};
                wildcard bins walking1_27 = {32'b????1???????????????????????????};
            `endif
            `ifdef SSCSRIND_SUPPORTED
                wildcard bins walking1_28 = {32'b???1????????????????????????????};
            `endif
            wildcard bins walking1_30 = {32'b?1??????????????????????????????};
            wildcard bins walking1_31 = {32'b1???????????????????????????????};
            wildcard bins walking0_1  = {32'b??????????????????????????????0?};
            wildcard bins walking0_2  = {32'b?????????????????????????????0??};
            // bins of high-half csrs

            wildcard bins walking0_22 = {32'b?????????0??????????????????????};
            wildcard bins walking0_23 = {32'b????????0???????????????????????};
            wildcard bins walking0_24 = {32'b???????0????????????????????????};
            wildcard bins walking0_25 = {32'b??????0?????????????????????????};
            wildcard bins walking0_26 = {32'b?????0??????????????????????????};
            wildcard bins walking0_27 = {32'b????0???????????????????????????};
            wildcard bins walking0_28 = {32'b???0????????????????????????????};
            wildcard bins walking0_29 = {32'b??0?????????????????????????????};
            wildcard bins walking0_30 = {32'b?0??????????????????????????????};
            wildcard bins walking0_31 = {32'b0???????????????????????????????};
        }
    `endif

    // ── Always-present feature coverpoints ───────────────────────────────
    `ifdef ZFINX_SUPPORTED
        misa_F: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "misa", "exts")[5] {
            bins F_set   = {1'b1};
            bins F_clear = {1'b0};
        }
        mstateen0_fcsr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "fcsr") {
            bins fcsr_zero = {1'b0};
            bins fcsr_one  = {1'b1};
        }
        cp_fcsr_ro_zero: cross misa_F, csrops, mstateen0_fcsr_bit {
            ignore_bins ig1 = binsof(misa_F.F_clear);
            ignore_bins ig2 = binsof(misa_F.F_set) && binsof(mstateen0_fcsr_bit.fcsr_one);
            bins fcsr_reads_zero = binsof(misa_F.F_set) && binsof(mstateen0_fcsr_bit.fcsr_zero);
        }
        fscr_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins fcsr = {CSR_FCSR};
        }
        fcsr_lower_mode_csrs: coverpoint ins.current.insn[31:20] {
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

    // cp_envcfg: Only present when Sm > 1.11 is supported
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

    // ── Zcmt-dependent coverpoints (cp_jvt_access) ──────────
    `ifdef ZCMT_SUPPORTED
        jvt_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_CURRENT, "mstateen0", "jvt") {
            bins jvt_disabled = {1'b0};
            bins jvt_enabled  = {1'b1};
        }
        jvt_csr: coverpoint ins.current.insn[31:20] {
            wildcard bins jvt = {CSR_JVT};
        }
    `endif

    // ── Sdtrig-dependent coverpoints (cp_context) ───────────────────────
    `ifdef SDTRIG_SUPPORTED
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

    // ── Sm1p13 + Hypervisor dependent coverpoints (cp_p1p13) ─────────────
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

    // ── Ssqosid-dependent coverpoints (cp_srmcfg) ────────────────────────

    `ifdef SSQOSID_SUPPORTED
        `ifdef UDB_MXLEN_64
            srmcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0", "srmcfg")[0] {
                bins srmcfg_disabled = {1'b0};
                bins srmcfg_enabled  = {1'b1};
            }
            srmcfg_csr: coverpoint ins.current.insn[31:20] {
                wildcard bins srmcfg = {CSR_SRMCFG};
            }
        `else
            srmcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0h", "srmcfg")[0] {
                bins srmcfg_disabled = {1'b0};
                bins srmcfg_enabled  = {1'b1};
            }
            srmcfg_csr: coverpoint ins.current.insn[31:20] {
                wildcard bins srmcfg = {CSR_SRMCFG};
            }
        `endif
    `endif

    // ── Sctr-dependent coverpoints (cp_ctr) ──────────────────────────────
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


    `ifdef SSSTATEEN_SUPPORTED
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
                bins se_disabled = {1'b0};
                bins se_enabled  = {1'b1};
            }
        `else
            mstateen_se_n: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0H) + int'(ins.current.insn[21:20]), "mstateenh", "mstateenh")[31] {
                bins se_disabled = {1'b0};
                bins se_enabled  = {1'b1};
            }
        `endif

        `ifdef UDB_MXLEN_64
            se0: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0", "se0")[0] {
                bins se0_disabled = {1'b0};
                bins se0_enabled  = {1'b1};
            }
        `else
            se0: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstateen0h", "se0")[0] {
                bins se0_disabled = {1'b0};
                bins se0_enabled  = {1'b1};
            }
        `endif
    `endif

    cp_csr_illegal_accesses: cross priv_mode_maybes_u, mstateen_csrs, csrops;
    cp_walking_ones: cross priv_mode_m, mstateen_walk_csrs, csrops, csr_walk;
    `ifdef SSSTATEEN_SUPPORTED
        cp_mstateen0_se0_controls_sstateen0: cross csrops, priv_mode_s, se0, sstateen0_csr;
        cp_mstateen_se_controls_sstateen123: cross csrops, priv_mode_s, mstateen_se_n, sstateen123_csrs;
    `endif

    `ifdef ZFINX_SUPPORTED
        cp_fcsr: cross misa_F, priv_mode_m, mstateen0_fcsr_bit, csrops, fscr_csr {
            ignore_bins ig1 = binsof(misa_F.F_set)  && binsof(mstateen0_fcsr_bit.fcsr_zero);
            ignore_bins ig2 = binsof(misa_F.F_set)  && binsof(fscr_csr.fcsr);
            ignore_bins ig3 = binsof(misa_F.F_clear) && binsof(mstateen0_fcsr_bit.fcsr_zero);
        }
        cp_fcsr_lower: cross priv_mode_maybes_u, misa_F, mstateen0_fcsr_bit, csrops, fcsr_lower_mode_csrs {
            ignore_bins ig1 = binsof(misa_F.F_set)  && binsof(mstateen0_fcsr_bit.fcsr_zero);
            ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(mstateen0_fcsr_bit.fcsr_zero);
        }
        cp_fcsr_fp_instrs: cross priv_mode_maybes_u, misa_F, mstateen0_fcsr_bit, fp_instrs {
            ignore_bins ig1 = binsof(misa_F.F_set)  && binsof(mstateen0_fcsr_bit.fcsr_zero);
            ignore_bins ig2 = binsof(misa_F.F_clear) && binsof(mstateen0_fcsr_bit.fcsr_zero);
        }
    `endif

    // Row 8: Sm > 1.11 only
    `ifdef SM1P12P0_OR_LATER_SUPPORTED
        cp_envcfg: cross csrops, priv_mode_m_maybes_u, senvcfg_csr, envcfg_state;
    `endif

    // Row 7: Zcmt only
    `ifdef ZCMT_SUPPORTED
        // The tests are disabled until Sail models Zcmt (JVT_TESTS in Smstateen.py), so this reports missing coverage
        cp_jvt_access:     cross priv_mode_maybes_u, csrops, jvt_csr, jvt_state;
    `endif

    // Row 12: Sdtrig only
    `ifdef SDTRIG_SUPPORTED
        cp_context: cross csrops, scontext_csr, context_state, priv_mode_m_maybes_u;
    `endif

    // Row 13: Sm1p13 + Hypervisor only
    `ifdef SM1P13P0_OR_LATER_SUPPORTED
        `ifdef H_SUPPORTED
            `ifdef UDB_MXLEN_32
                cp_p1p13: cross csrops, p1p13_state, hedelegh_csr, priv_mode_m_maybes_u;
            `endif
        `endif
    `endif

    // Row 14: Ssqosid only
    `ifdef SSQOSID_SUPPORTED
        cp_srmcfg: cross csrops, srmcfg_csr, srmcfg_state, priv_mode_m_maybes_u;
    `endif

    // Row 15: Sctr only
    `ifdef SSCTR_SUPPORTED
        // The tests are disabled until Sail models Smctr (CTR_TESTS in Smstateen.py), so this reports missing coverage
        cp_ctr: cross csrops, ctr_csrs, ctr_state, priv_mode_m_maybes_u;
    `endif
    `ifdef SSAIA_SUPPORTED
        // The tests are disabled until Sail models Ssaia (AIA_TESTS in Smstateen.py), so this reports missing coverage
        cp_imsic: cross csrops, imsic_csrs, imsic_state, priv_mode_m_maybes_u;
        cp_aia: cross csrops, aia_csrs, aia_state, priv_mode_m_maybes_u;
    `endif

endgroup

// H group: the base coverpoints crossed with HS-, VS- and VU-mode and, for the bits hstateen also has, with the
// matching hstateen bit.  The hstateen bit is read-only zero while the mstateen bit is 0, so each state is
// {mstateen bit, hstateen bit} = 00, 10 or 11.
`ifdef H_SUPPORTED
covergroup Smstateen_H_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    csrops: coverpoint ins.current.insn {
        wildcard bins csrw = {CSRRW};
        wildcard bins csrs = {CSRRS};
        wildcard bins csrc = {CSRRC};
    }

    // ── SE0-SE3: sstateen0-3 and hstateen0-3 ─────────────────────────────
    se0_csrs: coverpoint ins.current.insn[31:20] {
        bins sstateen0 = {CSR_SSTATEEN0};
        bins hstateen0 = {CSR_HSTATEEN0};
        `ifdef UDB_MXLEN_32
            bins hstateen0h = {CSR_HSTATEEN0H};
        `endif
    }
    sstateen123_csrs: coverpoint ins.current.insn[31:20] {
        bins sstateen1 = {CSR_SSTATEEN1};
        bins sstateen2 = {CSR_SSTATEEN2};
        bins sstateen3 = {CSR_SSTATEEN3};
        bins hstateen1 = {CSR_HSTATEEN1};
        bins hstateen2 = {CSR_HSTATEEN2};
        bins hstateen3 = {CSR_HSTATEEN3};
        `ifdef UDB_MXLEN_32
            bins hstateen1h = {CSR_HSTATEEN1H};
            bins hstateen2h = {CSR_HSTATEEN2H};
            bins hstateen3h = {CSR_HSTATEEN3H};
        `endif
    }
    // Bit 63 (bit 31 of the high half on RV32) of the mstateen<n> and hstateen<n> matching the CSR being accessed;
    // n is the low two bits of the CSR address
    `ifdef UDB_MXLEN_64
        se_n_state: coverpoint {
            get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0) + int'(ins.current.insn[21:20]), "mstateen", "mstateen")[63],
            get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_HSTATEEN0) + int'(ins.current.insn[21:20]), "hstateen", "hstateen")[63]} {
    `else
        se_n_state: coverpoint {
            get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0H) + int'(ins.current.insn[21:20]), "mstateenh", "mstateenh")[31],
            get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_HSTATEEN0H) + int'(ins.current.insn[21:20]), "hstateenh", "hstateenh")[31]} {
    `endif
        bins mstateen_zero = {2'b00};
        bins hstateen_zero = {2'b10};
        bins both_one      = {2'b11};
    }

    // ── ENVCFG: senvcfg and henvcfg ───────────────────────────────────────
    envcfg_csrs: coverpoint ins.current.insn[31:20] {
        bins senvcfg = {CSR_SENVCFG};
        bins henvcfg = {CSR_HENVCFG};
        `ifdef UDB_MXLEN_32
            bins henvcfgh = {CSR_HENVCFGH};
        `endif
    }
    `ifdef UDB_MXLEN_64
        envcfg_state: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0", "envcfg")[0],
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "envcfg")[0]} {
    `else
        envcfg_state: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0h", "envcfg")[0],
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0h", "envcfg")[0]} {
    `endif
        bins mstateen_zero = {2'b00};
        bins hstateen_zero = {2'b10};
        bins both_one      = {2'b11};
    }

    // ── CONTEXT: scontext and hcontext (Sdtrig) ───────────────────────────
    // No configuration has hcontext without scontext
    `ifdef UDB_SCONTEXT_IMPLEMENTED
        context_csrs: coverpoint ins.current.insn[31:20] {
            bins scontext = {CSR_SCONTEXT};
            `ifdef UDB_HCONTEXT_IMPLEMENTED
                bins hcontext = {CSR_HCONTEXT};
            `endif
        }
        `ifdef UDB_MXLEN_64
            context_state: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0", "context")[0],
                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0", "context")[0]} {
        `else
            context_state: coverpoint {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0h", "context")[0],
                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstateen0h", "context")[0]} {
        `endif
            bins mstateen_zero = {2'b00};
            bins hstateen_zero = {2'b10};
            bins both_one      = {2'b11};
        }
    `endif

    // ── P1P13: hedelegh, which exists only on RV32 from Priv 1.13 ─────────
    `ifdef SM1P13P0_OR_LATER_SUPPORTED
        `ifdef UDB_MXLEN_32
            p1p13_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0h", "p1p13")[0] {
                bins p1p13_disabled = {1'b0};
                bins p1p13_enabled  = {1'b1};
            }
            hedelegh_csr: coverpoint ins.current.insn[31:20] {
                bins hedelegh = {CSR_HEDELEGH};
            }
        `endif
    `endif

    // ── SRMCFG: srmcfg (Ssqosid) ──────────────────────────────────────────
    `ifdef SSQOSID_SUPPORTED
        `ifdef UDB_MXLEN_64
            srmcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0", "srmcfg")[0] {
                bins srmcfg_disabled = {1'b0};
                bins srmcfg_enabled  = {1'b1};
            }
        `else
            srmcfg_state: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstateen0h", "srmcfg")[0] {
                bins srmcfg_disabled = {1'b0};
                bins srmcfg_enabled  = {1'b1};
            }
        `endif
        srmcfg_csr: coverpoint ins.current.insn[31:20] {
            bins srmcfg = {CSR_SRMCFG};
        }
    `endif

    // ── Walking ones/zeros on hstateen0-3 from M-mode ─────────────────────
    hstateen_walk_csrs: coverpoint ins.current.insn[31:20] {
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
    // csrs sets the walking 1 and csrc clears the walking 0
    walk_ops: coverpoint ins.current.insn {
        wildcard bins csrs = {CSRRS};
        wildcard bins csrc = {CSRRC};
    }
    walk_bit: coverpoint $clog2(ins.current.rs1_val) iff ($onehot(ins.current.rs1_val)) {
        bins b[] = {[0:`UDB_MXLEN-1]};
    }
    // Bit 63 of the mstateen<n> matching hstateen<n>: the walks run with mstateen0-3 all zeros and all ones
    `ifdef UDB_MXLEN_64
        mstateen_se_n: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0) + int'(ins.current.insn[21:20]), "mstateen", "mstateen")[63] {
    `else
        mstateen_se_n: coverpoint get_csr_val_addr(ins.hart, ins.issue, `SAMPLE_BEFORE, int'(CSR_MSTATEEN0H) + int'(ins.current.insn[21:20]), "mstateenh", "mstateenh")[31] {
    `endif
        bins se_disabled = {1'b0};
        bins se_enabled  = {1'b1};
    }

    cp_walking_ones:                      cross priv_mode_m, hstateen_walk_csrs, walk_ops, walk_bit, mstateen_se_n;
    cp_mstateen0_se0_controls_sstateen0:  cross csrops, priv_mode_hs_vs_vu, se0_csrs, se_n_state;
    cp_mstateen_se_controls_sstateen123:  cross csrops, priv_mode_hs_vs_vu, sstateen123_csrs, se_n_state;
    cp_envcfg:                            cross csrops, priv_mode_hs_vs_vu, envcfg_csrs, envcfg_state;
    `ifdef UDB_SCONTEXT_IMPLEMENTED
        cp_context:                       cross csrops, priv_mode_hs_vs_vu, context_csrs, context_state;
    `endif
    `ifdef SM1P13P0_OR_LATER_SUPPORTED
        `ifdef UDB_MXLEN_32
            // HS-mode access to hedelegh is in Smstateen_cg/cp_p1p13, where S-mode is HS-mode
            cp_p1p13:                     cross csrops, priv_mode_vs_vu, hedelegh_csr, p1p13_state;
        `endif
    `endif
    `ifdef SSQOSID_SUPPORTED
        // The tests are disabled for now (SRMCFG_H_TESTS in Smstateen.py), so this reports missing coverage
        cp_srmcfg:                        cross csrops, priv_mode_hs_vs_vu, srmcfg_csr, srmcfg_state;
    `endif
endgroup
`endif

function void smstateen_sample(int hart, int issue, ins_t ins);
    Smstateen_cg.sample(ins);
    `ifdef H_SUPPORTED
        Smstateen_H_cg.sample(ins);
    `endif
endfunction
