///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage — Shared Coverpoints
//
// Pointer Masking coverpoints — common to Ssnpm, Smmpm, Smnpm(S), Smnpm(U).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Description:
//   Shared  coverpoint declarations for all pointer-masking
//   extension covergroups.
// Note:
//    RV64-only instructions (SD, AMO*_D, AMOCAS_Q, C_SD, C_SDSP, C_FSDSP, SSAMOSWAP_D,
//    VSE64_V, VSSE64_V, VSUXEI64_V, VSOXEI64_V) are not individually gated here because
//    pointer masking (Ssnpm/Smmpm/SmnpmS/smnpmU) is itself an RV64-only feature. Each extension's
//    coverage file is already guarded with `ifdef XLEN64, so these instructions will only
//    be compiled and exercised in a 64-bit configuration where they are legal.
//
///////////////////////////////////////////

    // cp_pmlen_masking_write
    // ---- All pointer-masking STORE instructions (write-side), carried out using A address ----
    pm_write_insn: coverpoint ins.current.insn {
        // Base integer stores
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        wildcard bins sd = {SD};
        // RV64A word-width atomics (Zaamo)
        `ifdef ZAAMO_SUPPORTED
            wildcard bins amoswap_w = {AMOSWAP_W};
            wildcard bins amoadd_w  = {AMOADD_W};
            wildcard bins amoxor_w  = {AMOXOR_W};
            wildcard bins amoand_w  = {AMOAND_W};
            wildcard bins amoor_w   = {AMOOR_W};
            wildcard bins amomin_w  = {AMOMIN_W};
            wildcard bins amomax_w  = {AMOMAX_W};
            wildcard bins amominu_w = {AMOMINU_W};
            wildcard bins amomaxu_w = {AMOMAXU_W};
            // RV64A double-width atomics
            wildcard bins amoswap_d = {AMOSWAP_D};
            wildcard bins amoadd_d  = {AMOADD_D};
            wildcard bins amoxor_d  = {AMOXOR_D};
            wildcard bins amoand_d  = {AMOAND_D};
            wildcard bins amoor_d   = {AMOOR_D};
            wildcard bins amomin_d  = {AMOMIN_D};
            wildcard bins amomax_d  = {AMOMAX_D};
            wildcard bins amominu_d = {AMOMINU_D};
            wildcard bins amomaxu_d = {AMOMAXU_D};
        `endif // ZAAMO_SUPPORTED
        // Zacas compare-and-swap
        `ifdef ZACAS_SUPPORTED
            wildcard bins amocas_w = {AMOCAS_W};
            wildcard bins amocas_d = {AMOCAS_D};
            wildcard bins amocas_q = {AMOCAS_Q};
        `endif // ZACAS_SUPPORTED
        // Zabha byte atomics
        `ifdef ZABHA_SUPPORTED
            wildcard bins amoswap_b = {AMOSWAP_B};
            wildcard bins amoadd_b  = {AMOADD_B};
            wildcard bins amoxor_b  = {AMOXOR_B};
            wildcard bins amoand_b  = {AMOAND_B};
            wildcard bins amoor_b   = {AMOOR_B};
            wildcard bins amomin_b  = {AMOMIN_B};
            wildcard bins amomax_b  = {AMOMAX_B};
            wildcard bins amominu_b = {AMOMINU_B};
            wildcard bins amomaxu_b = {AMOMAXU_B};
            // Zabha halfword atomics
            wildcard bins amoswap_h = {AMOSWAP_H};
            wildcard bins amoadd_h  = {AMOADD_H};
            wildcard bins amoxor_h  = {AMOXOR_H};
            wildcard bins amoand_h  = {AMOAND_H};
            wildcard bins amoor_h   = {AMOOR_H};
            wildcard bins amomin_h  = {AMOMIN_H};
            wildcard bins amomax_h  = {AMOMAX_H};
            wildcard bins amominu_h = {AMOMINU_H};
            wildcard bins amomaxu_h = {AMOMAXU_H};
        `endif // ZABHA_SUPPORTED
        // Floating-point stores
        `ifdef F_SUPPORTED
            wildcard bins fsw = {FSW};
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fsd = {FSD};
        `endif
        `ifdef Q_SUPPORTED
            wildcard bins fsq = {FSQ};
        `endif
        // Zca compressed stores
        `ifdef ZCA_SUPPORTED
            wildcard bins c_sw   = {C_SW};
            wildcard bins c_sd   = {C_SD};
            wildcard bins c_swsp = {C_SWSP};
            wildcard bins c_sdsp = {C_SDSP};
        `endif // ZCA_SUPPORTED
        // Zcd compressed double-precision FP store
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fsdsp = {C_FSDSP};
        `endif // ZCD_SUPPORTED
        // Zicboz cache-block zero (write effect)
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins cbo_zero = {CBO_ZERO};
        `endif
        // Zicbom cache-block maintenance (write effect)
        `ifdef ZICBOM_SUPPORTED
            wildcard bins cbo_clean = {CBO_CLEAN};
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_inval = {CBO_INVAL};
        `endif
        // Zicbop prefetch hints
        `ifdef ZICBOP_SUPPORTED
            wildcard bins prefetch_r = {PREFETCH_R};
            wildcard bins prefetch_w = {PREFETCH_W};
            wildcard bins prefetch_i = {PREFETCH_I};
        `endif
        // Zicfiss shadow-stack write-side instructions
        `ifdef ZICFISS_SUPPORTED
            wildcard bins sspush      = {SSPUSH};
            wildcard bins c_sspush    = {C_SSPUSH};
            wildcard bins ssamoswap_w = {SSAMOSWAP_W};
            wildcard bins ssamoswap_d = {SSAMOSWAP_D};
        `endif // ZICFISS_SUPPORTED
        // RVV 1.0 vector stores (ZVL32B minimum)
        `ifdef ZVL32B_SUPPORTED
            wildcard bins vse8_v      = {VSE8_V};
            wildcard bins vse16_v     = {VSE16_V};
            wildcard bins vse32_v     = {VSE32_V};
            wildcard bins vse64_v     = {VSE64_V};
            wildcard bins vsse32_v    = {VSSE32_V};
            wildcard bins vsse64_v    = {VSSE64_V};
            wildcard bins vsuxei32_v  = {VSUXEI32_V};
            wildcard bins vsuxei64_v  = {VSUXEI64_V};
            wildcard bins vsoxei32_v  = {VSOXEI32_V};
            wildcard bins vsoxei64_v  = {VSOXEI64_V};
            wildcard bins vs1r_v      = {VS1R_V};
            wildcard bins vsseg2e32_v = {VSSEG2E32_V};
        `endif // ZVL32B_SUPPORTED
    }

    // cp_pmlen_masking_read
    // ---- All pointer-masking LOAD instructions (read-side) , it will be using A_masked address ----
    pm_read_insn: coverpoint ins.current.insn {
        // Base integer loads
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw  = {LW};
        wildcard bins lwu = {LWU};
        wildcard bins ld  = {LD};
        // Floating-point loads
        `ifdef F_SUPPORTED
            wildcard bins flw = {FLW};
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fld = {FLD};
        `endif
        `ifdef Q_SUPPORTED
            wildcard bins flq = {FLQ};
        `endif
        // Zca compressed loads
        `ifdef ZCA_SUPPORTED
            wildcard bins c_lw   = {C_LW};
            wildcard bins c_ld   = {C_LD};
            wildcard bins c_lwsp = {C_LWSP};
            wildcard bins c_ldsp = {C_LDSP};
        `endif // ZCA_SUPPORTED
        // Zcd compressed double-precision FP load
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fldsp = {C_FLDSP};
        `endif // ZCD_SUPPORTED
        // Zicfiss shadow-stack read-side instructions
        `ifdef ZICFISS_SUPPORTED
            wildcard bins sspopchk   = {SSPOPCHK};
            wildcard bins c_sspopchk = {C_SSPOPCHK};
        `endif // ZICFISS_SUPPORTED
        // RVV 1.0 vector loads (ZVL32B minimum)
        `ifdef ZVL32B_SUPPORTED
            // Unit-stride loads
            wildcard bins vle8_v  = {VLE8_V};
            wildcard bins vle16_v = {VLE16_V};
            wildcard bins vle32_v = {VLE32_V};
            wildcard bins vle64_v = {VLE64_V};
            // Strided loads
            wildcard bins vlse32_v = {VLSE32_V};
            wildcard bins vlse64_v = {VLSE64_V};
            // Indexed unordered loads
            wildcard bins vluxei32_v = {VLUXEI32_V};
            wildcard bins vluxei64_v = {VLUXEI64_V};
            // Indexed ordered loads
            wildcard bins vloxei32_v = {VLOXEI32_V};
            wildcard bins vloxei64_v = {VLOXEI64_V};
            // Whole-register load
            wildcard bins vl1r_v = {VL1R_V};
            // Fault-only-first unit-stride loads
            wildcard bins vle8ff_v  = {VLE8FF_V};
            wildcard bins vle16ff_v = {VLE16FF_V};
            wildcard bins vle32ff_v = {VLE32FF_V};
            wildcard bins vle64ff_v = {VLE64FF_V};
            // Segmented loads (Nf=2 representative)
            wildcard bins vlseg2e32_v = {VLSEG2E32_V};
        `endif // ZVL32B_SUPPORTED
    }
    sw_insn:  coverpoint ins.current.insn { wildcard bins sw  = {SW};  }
    lw_insn:  coverpoint ins.current.insn { wildcard bins lw  = {LW};  }
    // ---- satp mode  ----
    satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
        bins bare = {4'b0000};
        `ifdef SV39_SUPPORTED
            bins sv39 = {4'b1000};
        `endif
        `ifdef SV48_SUPPORTED
            bins sv48 = {4'b1001};
        `endif
        `ifdef SV57_SUPPORTED
            bins sv57 = {4'b1010};
        `endif
    }
    a_upper_bits: coverpoint (ins.current.rs1_val + ins.current.imm)[63:48] {
        bins upper_0000 = {16'h0000};
        bins upper_0001 = {16'h0001};
        bins upper_0100 = {16'h0100};
        bins upper_0200 = {16'h0200};
        bins upper_8000 = {16'h8000};
        bins upper_FFFF = {16'hFFFF};
        bins upper_FE00 = {16'hFE00};
        bins upper_FF00 = {16'hFF00};
    }
    jalr_a_upper_bits_nonzero: coverpoint ins.current.csr[CSR_MTVAL][63:48] {
        bins upper_0001 = {16'h0001};
        bins upper_0100 = {16'h0100};
        bins upper_0200 = {16'h0200};
        bins upper_8000 = {16'h8000};
        bins upper_FFFF = {16'hFFFF};
        bins upper_FE00 = {16'hFE00};
        bins upper_FF00 = {16'hFF00};
        // upper_0000 excluded — would mean masking was incorrectly applied
    }
    // ---- Misaligned instruction ----
    // Misaligned address (e.g. scratch+1); upper 7 bits = 0x01 or 0x00
    misaligned_addr: coverpoint (ins.current.rs1_val + ins.current.imm)[1:0]
        iff (ins.current.insn inside {LW, SW}) {
        bins misaligned = {[2'b01:2'b11]};
    }
    misaligned_a_upper7: coverpoint (ins.current.rs1_val + ins.current.imm)[63:57] {
        bins upper_zero = {7'b0000000};
        bins upper_one  = {7'b0000001};
    }
    // ---- JALR instruction ----
    jalr_insn: coverpoint ins.current.insn {
        wildcard bins jalr = {JALR};
    }
    // for CBO.ZERO readback value
    zero_loaded: coverpoint ins.current.rd_val[63:0] {
        bins zero = {64'h0000_0000_0000_0000};
    }
    // For hardware csr writes, we raise an exception.
    illegal_addr: coverpoint (ins.current.rs1_val + ins.current.imm)[47:0] {
        bins is_illegal_base = {`RVMODEL_ACCESS_FAULT_ADDRESS[47:0]};
    }
    //To check whether any exception did occur.
    exception_occurred: coverpoint ins.current.csr[CSR_SCAUSE] {
        bins any_exception = {[64'h1 : 64'hFFFF_FFFF_FFFF_FFFF]};
    }
    pm_misalign_write : cross  pmm_active, misaligned_a_upper7, sw_insn, misaligned_addr;
    pm_misalign_read  : cross  pmm_active, misaligned_a_upper7, lw_insn, misaligned_addr;
    pm_read_fault     : cross illegal_addr, a_upper_bits, lw_insn ;
    pm_write_fault    : cross illegal_addr, a_upper_bits, sw_insn ;
