///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage — Shared Coverpoints
//
// PMM instruction coverpoints — common to Ssnpm, Smmpm, Smnpm(S), Smnpm(U).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Description:
//   Shared instruction coverpoint declarations for all pointer-masking
//   extension covergroups.  Covers every instruction category whose
//   effective address is subject to PMM masking:
//
//     - Base integer loads  (lb, lbu, lh, lhu, lw, lwu, ld)
//     - Base integer stores (sb, sh, sw, sd)
//     - RV64A word/doubleword atomics        [ZAAMO_SUPPORTED]
//     - Zacas compare-and-swap              [ZACAS_SUPPORTED]
//     - Zabha byte/halfword atomics          [ZABHA_SUPPORTED]
//     - Floating-point loads/stores          [F/D/Q_SUPPORTED]
//     - Zca compressed loads/stores          [ZCA_SUPPORTED]
//     - Zcd compressed FP loads/stores       [ZCD_SUPPORTED]
//     - Zicboz cache-block zero              [ZICBOZ_SUPPORTED]
//     - Zicbom cache-block maintenance       [ZICBOM_SUPPORTED]
//     - Zicbop prefetch hints                [ZICBOP_SUPPORTED]
//     - Zicfiss shadow-stack instructions    [ZICFISS_SUPPORTED]
//     - RVV 1.0 vector loads/stores          [ZVL32B_SUPPORTED]
//
///////////////////////////////////////////

    // ---- Base integer STORE instructions ----
    sb_insn:  coverpoint ins.current.insn { wildcard bins sb  = {SB};  }
    sh_insn:  coverpoint ins.current.insn { wildcard bins sh  = {SH};  }
    sw_insn:  coverpoint ins.current.insn { wildcard bins sw  = {SW};  }
    sd_insn:  coverpoint ins.current.insn { wildcard bins sd  = {SD};  }
    // ---- Base integer LOAD instructions ----
    lb_insn:  coverpoint ins.current.insn { wildcard bins lb  = {LB};  }
    lbu_insn: coverpoint ins.current.insn { wildcard bins lbu = {LBU}; }
    lh_insn:  coverpoint ins.current.insn { wildcard bins lh  = {LH};  }
    lhu_insn: coverpoint ins.current.insn { wildcard bins lhu = {LHU}; }
    lw_insn:  coverpoint ins.current.insn { wildcard bins lw  = {LW};  }
    lwu_insn: coverpoint ins.current.insn { wildcard bins lwu = {LWU}; }
    ld_insn:  coverpoint ins.current.insn { wildcard bins ld  = {LD};  }
    // ---- RV64A atomic instructions (Zaamo) ----
    `ifdef ZAAMO_SUPPORTED
        // word-width atomics
        amoswap_w_insn:  coverpoint ins.current.insn { wildcard bins amoswap_w  = {AMOSWAP_W};  }
        amoadd_w_insn:   coverpoint ins.current.insn { wildcard bins amoadd_w   = {AMOADD_W};   }
        amoxor_w_insn:   coverpoint ins.current.insn { wildcard bins amoxor_w   = {AMOXOR_W};   }
        amoand_w_insn:   coverpoint ins.current.insn { wildcard bins amoand_w   = {AMOAND_W};   }
        amoor_w_insn:    coverpoint ins.current.insn { wildcard bins amoor_w    = {AMOOR_W};    }
        amomin_w_insn:   coverpoint ins.current.insn { wildcard bins amomin_w   = {AMOMIN_W};   }
        amomax_w_insn:   coverpoint ins.current.insn { wildcard bins amomax_w   = {AMOMAX_W};   }
        amominu_w_insn:  coverpoint ins.current.insn { wildcard bins amominu_w  = {AMOMINU_W};  }
        amomaxu_w_insn:  coverpoint ins.current.insn { wildcard bins amomaxu_w  = {AMOMAXU_W};  }
        // double-width atomics
        amoswap_d_insn:  coverpoint ins.current.insn { wildcard bins amoswap_d  = {AMOSWAP_D};  }
        amoadd_d_insn:   coverpoint ins.current.insn { wildcard bins amoadd_d   = {AMOADD_D};   }
        amoxor_d_insn:   coverpoint ins.current.insn { wildcard bins amoxor_d   = {AMOXOR_D};   }
        amoand_d_insn:   coverpoint ins.current.insn { wildcard bins amoand_d   = {AMOAND_D};   }
        amoor_d_insn:    coverpoint ins.current.insn { wildcard bins amoor_d    = {AMOOR_D};    }
        amomin_d_insn:   coverpoint ins.current.insn { wildcard bins amomin_d   = {AMOMIN_D};   }
        amomax_d_insn:   coverpoint ins.current.insn { wildcard bins amomax_d   = {AMOMAX_D};   }
        amominu_d_insn:  coverpoint ins.current.insn { wildcard bins amominu_d  = {AMOMINU_D};  }
        amomaxu_d_insn:  coverpoint ins.current.insn { wildcard bins amomaxu_d  = {AMOMAXU_D};  }
    `endif // ZAAMO_SUPPORTED
    // ---- Zacas compare-and-swap instructions ----
    `ifdef ZACAS_SUPPORTED
        amocas_w_insn: coverpoint ins.current.insn { wildcard bins amocas_w = {AMOCAS_W}; }
        amocas_d_insn: coverpoint ins.current.insn { wildcard bins amocas_d = {AMOCAS_D}; }
        amocas_q_insn: coverpoint ins.current.insn { wildcard bins amocas_q = {AMOCAS_Q}; }
    `endif // ZACAS_SUPPORTED
    // ---- Zabha byte/halfword atomics ----
    `ifdef ZABHA_SUPPORTED
        // byte atomics
        amoswap_b_insn:  coverpoint ins.current.insn { wildcard bins amoswap_b  = {AMOSWAP_B};  }
        amoadd_b_insn:   coverpoint ins.current.insn { wildcard bins amoadd_b   = {AMOADD_B};   }
        amoxor_b_insn:   coverpoint ins.current.insn { wildcard bins amoxor_b   = {AMOXOR_B};   }
        amoand_b_insn:   coverpoint ins.current.insn { wildcard bins amoand_b   = {AMOAND_B};   }
        amoor_b_insn:    coverpoint ins.current.insn { wildcard bins amoor_b    = {AMOOR_B};    }
        amomin_b_insn:   coverpoint ins.current.insn { wildcard bins amomin_b   = {AMOMIN_B};   }
        amomax_b_insn:   coverpoint ins.current.insn { wildcard bins amomax_b   = {AMOMAX_B};   }
        amominu_b_insn:  coverpoint ins.current.insn { wildcard bins amominu_b  = {AMOMINU_B};  }
        amomaxu_b_insn:  coverpoint ins.current.insn { wildcard bins amomaxu_b  = {AMOMAXU_B};  }
        // halfword atomics
        amoswap_h_insn:  coverpoint ins.current.insn { wildcard bins amoswap_h  = {AMOSWAP_H};  }
        amoadd_h_insn:   coverpoint ins.current.insn { wildcard bins amoadd_h   = {AMOADD_H};   }
        amoxor_h_insn:   coverpoint ins.current.insn { wildcard bins amoxor_h   = {AMOXOR_H};   }
        amoand_h_insn:   coverpoint ins.current.insn { wildcard bins amoand_h   = {AMOAND_H};   }
        amoor_h_insn:    coverpoint ins.current.insn { wildcard bins amoor_h    = {AMOOR_H};    }
        amomin_h_insn:   coverpoint ins.current.insn { wildcard bins amomin_h   = {AMOMIN_H};   }
        amomax_h_insn:   coverpoint ins.current.insn { wildcard bins amomax_h   = {AMOMAX_H};   }
        amominu_h_insn:  coverpoint ins.current.insn { wildcard bins amominu_h  = {AMOMINU_H};  }
        amomaxu_h_insn:  coverpoint ins.current.insn { wildcard bins amomaxu_h  = {AMOMAXU_H};  }
    `endif // ZABHA_SUPPORTED
    // ---- Floating-point load/store instructions ----
    `ifdef F_SUPPORTED
        flw_insn: coverpoint ins.current.insn { wildcard bins flw = {FLW}; }
        fsw_insn: coverpoint ins.current.insn { wildcard bins fsw = {FSW}; }
    `endif
    `ifdef D_SUPPORTED
        fld_insn: coverpoint ins.current.insn { wildcard bins fld = {FLD}; }
        fsd_insn: coverpoint ins.current.insn { wildcard bins fsd = {FSD}; }
    `endif
    `ifdef Q_SUPPORTED
        flq_insn: coverpoint ins.current.insn { wildcard bins flq = {FLQ}; }
        fsq_insn: coverpoint ins.current.insn { wildcard bins fsq = {FSQ}; }
    `endif
    // ---- Zca compressed load/store instructions ----
    `ifdef ZCA_SUPPORTED
        c_lw_insn:   coverpoint ins.current.insn { wildcard bins c_lw   = {C_LW};   }
        c_ld_insn:   coverpoint ins.current.insn { wildcard bins c_ld   = {C_LD};   }
        c_sw_insn:   coverpoint ins.current.insn { wildcard bins c_sw   = {C_SW};   }
        c_sd_insn:   coverpoint ins.current.insn { wildcard bins c_sd   = {C_SD};   }
        c_lwsp_insn: coverpoint ins.current.insn { wildcard bins c_lwsp = {C_LWSP}; }
        c_ldsp_insn: coverpoint ins.current.insn { wildcard bins c_ldsp = {C_LDSP}; }
        c_swsp_insn: coverpoint ins.current.insn { wildcard bins c_swsp = {C_SWSP}; }
        c_sdsp_insn: coverpoint ins.current.insn { wildcard bins c_sdsp = {C_SDSP}; }
    `endif // ZCA_SUPPORTED
    // ---- Zcd compressed double-precision FP load/store (SP-relative) ----
    `ifdef ZCD_SUPPORTED
        c_fldsp_insn: coverpoint ins.current.insn { wildcard bins c_fldsp = {C_FLDSP}; }
        c_fsdsp_insn: coverpoint ins.current.insn { wildcard bins c_fsdsp = {C_FSDSP}; }
    `endif // ZCD_SUPPORTED
    // ---- Zicboz cache-block zero ----
    `ifdef ZICBOZ_SUPPORTED
        cbo_zero_insn: coverpoint ins.current.insn { wildcard bins cbo_zero = {CBO_ZERO}; }
    `endif
    // ---- Zicbom cache-block maintenance ----
    `ifdef ZICBOM_SUPPORTED
        cbo_clean_insn: coverpoint ins.current.insn { wildcard bins cbo_clean = {CBO_CLEAN}; }
        cbo_flush_insn: coverpoint ins.current.insn { wildcard bins cbo_flush = {CBO_FLUSH}; }
        cbo_inval_insn: coverpoint ins.current.insn { wildcard bins cbo_inval = {CBO_INVAL}; }
    `endif
    // ---- Zicbop prefetch hints ----
    `ifdef ZICBOP_SUPPORTED
        prefetch_r_insn: coverpoint ins.current.insn { wildcard bins prefetch_r = {PREFETCH_R}; }
        prefetch_w_insn: coverpoint ins.current.insn { wildcard bins prefetch_w = {PREFETCH_W}; }
        prefetch_i_insn: coverpoint ins.current.insn { wildcard bins prefetch_i = {PREFETCH_I}; }
    `endif
    // ---- Zicfiss shadow-stack instructions ----
    `ifdef ZICFISS_SUPPORTED
        sspush_insn:        coverpoint ins.current.insn { wildcard bins sspush        = {SSPUSH};        }
        c_sspush_insn:      coverpoint ins.current.insn { wildcard bins c_sspush      = {C_SSPUSH};      }
        sspopchk_insn:      coverpoint ins.current.insn { wildcard bins sspopchk      = {SSPOPCHK};      }
        c_sspopchk_insn:    coverpoint ins.current.insn { wildcard bins c_sspopchk    = {C_SSPOPCHK};    }
        ssamoswap_w_insn:   coverpoint ins.current.insn { wildcard bins ssamoswap_w   = {SSAMOSWAP_W};   }
        ssamoswap_d_insn:   coverpoint ins.current.insn { wildcard bins ssamoswap_d   = {SSAMOSWAP_D};   }
    `endif // ZICFISS_SUPPORTED
    // ---- RVV 1.0 vector load/store instructions (ZVI32B minimum) ----
    `ifdef ZVL32B_SUPPORTED
        // unit-stride loads
        vle8_v_insn:   coverpoint ins.current.insn { wildcard bins vle8_v   = {VLE8_V};   }
        vle16_v_insn:  coverpoint ins.current.insn { wildcard bins vle16_v  = {VLE16_V};  }
        vle32_v_insn:  coverpoint ins.current.insn { wildcard bins vle32_v  = {VLE32_V};  }
        vle64_v_insn:  coverpoint ins.current.insn { wildcard bins vle64_v  = {VLE64_V};  }
        // unit-stride stores
        vse8_v_insn:   coverpoint ins.current.insn { wildcard bins vse8_v   = {VSE8_V};   }
        vse16_v_insn:  coverpoint ins.current.insn { wildcard bins vse16_v  = {VSE16_V};  }
        vse32_v_insn:  coverpoint ins.current.insn { wildcard bins vse32_v  = {VSE32_V};  }
        vse64_v_insn:  coverpoint ins.current.insn { wildcard bins vse64_v  = {VSE64_V};  }
        // strided loads / stores
        vlse32_v_insn: coverpoint ins.current.insn { wildcard bins vlse32_v = {VLSE32_V}; }
        vlse64_v_insn: coverpoint ins.current.insn { wildcard bins vlse64_v = {VLSE64_V}; }
        vsse32_v_insn: coverpoint ins.current.insn { wildcard bins vsse32_v = {VSSE32_V}; }
        vsse64_v_insn: coverpoint ins.current.insn { wildcard bins vsse64_v = {VSSE64_V}; }
        // indexed unordered loads / stores
        vluxei32_v_insn: coverpoint ins.current.insn { wildcard bins vluxei32_v = {VLUXEI32_V}; }
        vluxei64_v_insn: coverpoint ins.current.insn { wildcard bins vluxei64_v = {VLUXEI64_V}; }
        vsuxei32_v_insn: coverpoint ins.current.insn { wildcard bins vsuxei32_v = {VSUXEI32_V}; }
        vsuxei64_v_insn: coverpoint ins.current.insn { wildcard bins vsuxei64_v = {VSUXEI64_V}; }
        // indexed ordered loads / stores
        vloxei32_v_insn: coverpoint ins.current.insn { wildcard bins vloxei32_v = {VLOXEI32_V}; }
        vloxei64_v_insn: coverpoint ins.current.insn { wildcard bins vloxei64_v = {VLOXEI64_V}; }
        vsoxei32_v_insn: coverpoint ins.current.insn { wildcard bins vsoxei32_v = {VSOXEI32_V}; }
        vsoxei64_v_insn: coverpoint ins.current.insn { wildcard bins vsoxei64_v = {VSOXEI64_V}; }
        // whole-register load / store
        vl1r_v_insn:  coverpoint ins.current.insn { wildcard bins vl1r_v  = {VL1R_V};  }
        vs1r_v_insn:  coverpoint ins.current.insn { wildcard bins vs1r_v  = {VS1R_V};  }
        // fault-only-first unit-stride loads
        vle8ff_v_insn:  coverpoint ins.current.insn { wildcard bins vle8ff_v  = {VLE8FF_V};  }
        vle16ff_v_insn: coverpoint ins.current.insn { wildcard bins vle16ff_v = {VLE16FF_V}; }
        vle32ff_v_insn: coverpoint ins.current.insn { wildcard bins vle32ff_v = {VLE32FF_V}; }
        vle64ff_v_insn: coverpoint ins.current.insn { wildcard bins vle64ff_v = {VLE64FF_V}; }
        // segmented loads / stores (Nf=2 representative)
        vlseg2e32_v_insn: coverpoint ins.current.insn { wildcard bins vlseg2e32_v = {VLSEG2E32_V}; }
        vsseg2e32_v_insn: coverpoint ins.current.insn { wildcard bins vsseg2e32_v = {VSSEG2E32_V}; }
    `endif // ZVL32B_SUPPORTED
