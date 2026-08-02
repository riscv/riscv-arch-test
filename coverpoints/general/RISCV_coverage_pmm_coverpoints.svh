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
// Note: RV64-only instructions (SD, AMO*_D, AMOCAS_Q, C_SD, C_SDSP, C_FSDSP, SSAMOSWAP_D,
//       VSE64_V, VSSE64_V, VSUXEI64_V, VSOXEI64_V) are not individually gated here because
//       pointer masking (Ssnpm/Smmpm/SmnpmS/smnpmU) is itself an RV64-only feature. so these instructions will only
//       be compiled and exercised in a 64-bit configuration where they are legal.
//
///////////////////////////////////////////
    pm_insn: coverpoint ins.current.insn {
        type_option.weight = 0;
        // Base integer stores
        wildcard bins sb  = {SB};
        wildcard bins sh  = {SH};
        wildcard bins sw  = {SW};
        wildcard bins sd  = {SD};
        // Base integer loads
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lw  = {LW};
        wildcard bins lwu = {LWU};
        wildcard bins ld  = {LD};
        // RV64A / Zaamo atomics (treated as write operation for masking coverage)
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
            wildcard bins amoswap_d = {AMOSWAP_D};
            wildcard bins amoadd_d  = {AMOADD_D};
            wildcard bins amoxor_d  = {AMOXOR_D};
            wildcard bins amoand_d  = {AMOAND_D};
            wildcard bins amoor_d   = {AMOOR_D};
            wildcard bins amomin_d  = {AMOMIN_D};
            wildcard bins amomax_d  = {AMOMAX_D};
            wildcard bins amominu_d = {AMOMINU_D};
            wildcard bins amomaxu_d = {AMOMAXU_D};
            // Zacas compare-and-swap
            `ifdef ZACAS_SUPPORTED
                wildcard bins amocas_w = {AMOCAS_W};
                wildcard bins amocas_d = {AMOCAS_D};
                //wildcard bins amocas_q = {AMOCAS_Q}; Not supported
            `endif // ZACAS_SUPPORTED
            // Zabha byte/halfword atomics
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
        `endif // ZAAMO_SUPPORTED
        // Floating-point stores and loads
        `ifdef F_SUPPORTED
            wildcard bins fsw = {FSW};
            wildcard bins flw = {FLW};
        `endif
        `ifdef D_SUPPORTED
            wildcard bins fsd = {FSD};
            wildcard bins fld = {FLD};
        `endif
        `ifdef Q_SUPPORTED
            wildcard bins fsq = {FSQ};
            wildcard bins flq = {FLQ};
        `endif
        // Zca compressed stores and loads
        `ifdef ZCA_SUPPORTED
            wildcard bins c_sw   = {C_SW};
            wildcard bins c_sd   = {C_SD};
            wildcard bins c_swsp = {C_SWSP};
            wildcard bins c_sdsp = {C_SDSP};
            wildcard bins c_lw   = {C_LW};
            wildcard bins c_ld   = {C_LD};
            wildcard bins c_lwsp = {C_LWSP};
            wildcard bins c_ldsp = {C_LDSP};
            // Zcd compressed double-precision FP store and load
        `ifdef ZCD_SUPPORTED
            wildcard bins c_fsdsp = {C_FSDSP};
            wildcard bins c_fldsp = {C_FLDSP};
        `endif // ZCD_SUPPORTED
        `endif // ZCA_SUPPORTED
        // Zicboz cache-block zero (write, address in rs1)
        `ifdef ZICBOZ_SUPPORTED
            wildcard bins cbo_zero = {CBO_ZERO};
        `endif
        // Zicbom cache-block maintenance (write, address in rs1)
        `ifdef ZICBOM_SUPPORTED
            wildcard bins cbo_clean = {CBO_CLEAN};
            wildcard bins cbo_flush = {CBO_FLUSH};
            wildcard bins cbo_inval = {CBO_INVAL};
        `endif
        // Zicbop prefetch hints (address in rs1)
        `ifdef ZICBOP_SUPPORTED
            wildcard bins prefetch_r = {PREFETCH_R};
            wildcard bins prefetch_w = {PREFETCH_W};
            wildcard bins prefetch_i = {PREFETCH_I};
        `endif
        // Zicfiss shadow-stack stores and loads
        `ifdef ZICFISS_SUPPORTED
            //wildcard bins sspush      = {SSPUSH}; in framework/src/act/fcov/coverage/RISCV_imported_decode_pkg.svh we have localparam [31:0]  SSPUSH_X1  and SSPUSH_X5
            //wildcard bins c_sspush    = {C_SSPUSH};
            wildcard bins ssamoswap_w = {SSAMOSWAP_W};
            wildcard bins ssamoswap_d = {SSAMOSWAP_D};
            //wildcard bins sspopchk    = {SSPOPCHK};
            //wildcard bins c_sspopchk  = {C_SSPOPCHK};
        `endif // ZICFISS_SUPPORTED
        // RVV 1.0 vector stores and loads (ZVL32B minimum)
        `ifdef ZVL32B_SUPPORTED
            // Vector stores
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
            // Vector loads
            wildcard bins vle8_v      = {VLE8_V};
            wildcard bins vle16_v     = {VLE16_V};
            wildcard bins vle32_v     = {VLE32_V};
            wildcard bins vle64_v     = {VLE64_V};
            wildcard bins vlse32_v    = {VLSE32_V};
            wildcard bins vlse64_v    = {VLSE64_V};
            wildcard bins vluxei32_v  = {VLUXEI32_V};
            wildcard bins vluxei64_v  = {VLUXEI64_V};
            wildcard bins vloxei32_v  = {VLOXEI32_V};
            wildcard bins vloxei64_v  = {VLOXEI64_V};
            wildcard bins vl1r_v      = {VL1R_V};
            wildcard bins vle8ff_v    = {VLE8FF_V};
            wildcard bins vle16ff_v   = {VLE16FF_V};
            wildcard bins vle32ff_v   = {VLE32FF_V};
            wildcard bins vle64ff_v   = {VLE64FF_V};
            wildcard bins vlseg2e32_v = {VLSEG2E32_V};
        `endif // ZVL32B_SUPPORTED
    }

    sw_lw_insn:  coverpoint ins.current.insn {
        type_option.weight = 0;
         wildcard bins sw  = {SW};
         wildcard bins lw  = {LW};
    }
    satp_mode: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") {
        type_option.weight = 0;
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
    a_upper_bits: coverpoint ((ins.current.rs1_val + ins.current.imm)>> 48) {
        type_option.weight = 0;
        bins upper_0000 = {16'h0000};   // Unaffected by pointer masking
        bins upper_0001 = {16'h0001};   // Bit 48 masked if PMLEN=16 but not 7
        bins upper_0100 = {16'h0100};   // Bit 56 masked if PMLEN=16 but not 7
        bins upper_0200 = {16'h0200};   // Bit 57 masked if PMLEN=16 or 7
        bins upper_8000 = {16'h8000};   // Bit 63 masked if PMLEN=16 or 7
        bins upper_FFFF = {16'hFFFF};   // Bits 63:48 masked if PMLEN=16, only partially if PMLEN=7
        bins upper_FE00 = {16'hFE00};   // Bits 63:57 masked if PMLEN=16 or 7
        bins upper_FF00 = {16'hFF00};   // Bits 63:56 masked if PMLEN=16, only partially if PMLEN=7
    }
    jalr_insn: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins jalr = {JALR};
    }
    csrw_insn: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins csrrw = {CSRW};
    }

    // Misaligned address (e.g. scratch+1); upper 7 bits = 0x01 or 0x00
    misaligned_addr: coverpoint ((ins.current.rs1_val + ins.current.imm) & 2'b11) {
        type_option.weight = 0;
        bins misaligned = {[2'b01:2'b11]};
    }
    // ---- Misalign common cross dimensions ----
    pm_misalign : cross pmm, a_upper_bits, sw_lw_insn, misaligned_addr;

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        // Exception should write xtval with masked version of pointer.
        // Match on the UNMASKED low 48 bits only: the probe forms its address as
        // (tag << 48) | RVMODEL_ACCESS_FAULT_ADDRESS, so every a_upper_bits tag
        // shares the same low half. Masking the compare to 48 bits is what lets
        // this coverpoint cross with all 8 a_upper_bits bins; comparing the whole
        // address (or its high bits) would restrict pm_fault to the upper_0000 bin.
        // Part-selecting an expression is illegal in SystemVerilog, hence the AND.
        illegal_addr: coverpoint ((ins.current.rs1_val + ins.current.imm) & 48'hFFFF_FFFF_FFFF) {
            type_option.weight = 0;
            bins is_illegal_base = {`RVMODEL_ACCESS_FAULT_ADDRESS& 48'hFFFF_FFFF_FFFF};
        }
        pm_fault : cross pmm, a_upper_bits, sw_lw_insn, illegal_addr;
    `endif
