///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Ammarah Wakeel  email:ammarahwakeel9@gmail.com (UET, MAY 2026)
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
// Description: Coverage for Zama16b extension - Misaligned atomicity granule of 16 bytes.
//              Verifies that misaligned loads, stores, and AMOs that do not cross a
//              naturally aligned 16-byte boundary do not raise a misaligned fault.
//
//              Access-size -> valid offset range:
//                1-byte  (lb, lbu, sb, amo*.b)            : offsets [0:15]
//                2-byte  (lh, lhu, sh, flh, fsh, amo*.h)  : offsets [0:14]
//                4-byte  (lw, lwu, sw, flw, fsw, amo*.w)  : offsets [0:12]
//                8-byte  (ld, sd, fld, fsd, amo*.d)       : offsets [0:8]
//               16-byte  (flq, fsq, amocas.q)             : offsets [0:0]
//
// NOTE: This coverage only checks for no misaligned fault.
//       Multimaster testing will be required to verify atomicity.
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_ZAMA16B

covergroup Zama16b_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ================================================================
    // 1-byte accesses (lb, lbu, sb, amo*.b): offsets [0:15]
    // ================================================================
    insn_1byte: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        wildcard bins sb  = {SB};
        `ifdef ZAAMO_SUPPORTED
            `ifdef ZABHA_SUPPORTED
                wildcard bins amoswap_b = {AMOSWAP_B};
                wildcard bins amoadd_b  = {AMOADD_B};
                wildcard bins amoand_b  = {AMOAND_B};
                wildcard bins amoor_b   = {AMOOR_B};
                wildcard bins amoxor_b  = {AMOXOR_B};
                wildcard bins amomax_b  = {AMOMAX_B};
                wildcard bins amomaxu_b = {AMOMAXU_B};
                wildcard bins amomin_b  = {AMOMIN_B};
                wildcard bins amominu_b = {AMOMINU_B};
            `endif // ZABHA_SUPPORTED
        `endif // ZAAMO_SUPPORTED
    }
    offset_1byte: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) {
        type_option.weight = 0;
        bins offsets[] = {[0:15]};
    }
    cp_zama16b_1byte: cross insn_1byte, offset_1byte;

    // ================================================================
    // 2-byte accesses (lh, lhu, sh, flh, fsh, amo*.h): offsets [0:14]
    // ================================================================
    insn_2byte: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins sh  = {SH};
        `ifdef ZFH_SUPPORTED
            wildcard bins flh = {FLH};
            wildcard bins fsh = {FSH};
        `endif // ZFH_SUPPORTED
        `ifdef ZAAMO_SUPPORTED
            `ifdef ZABHA_SUPPORTED
                wildcard bins amoswap_h = {AMOSWAP_H};
                wildcard bins amoadd_h  = {AMOADD_H};
                wildcard bins amoand_h  = {AMOAND_H};
                wildcard bins amoor_h   = {AMOOR_H};
                wildcard bins amoxor_h  = {AMOXOR_H};
                wildcard bins amomax_h  = {AMOMAX_H};
                wildcard bins amomaxu_h = {AMOMAXU_H};
                wildcard bins amomin_h  = {AMOMIN_H};
                wildcard bins amominu_h = {AMOMINU_H};
            `endif // ZABHA_SUPPORTED
        `endif // ZAAMO_SUPPORTED
    }
    offset_2byte: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) {
        type_option.weight = 0;
        bins offsets[] = {[0:14]};
    }
    cp_zama16b_2byte: cross insn_2byte, offset_2byte;

    // ================================================================
    // 4-byte accesses (lw, lwu, sw, flw, fsw, amo*.w, amocas.w): offsets [0:12]
    // ================================================================
    insn_4byte: coverpoint ins.current.insn {
        type_option.weight = 0;
        wildcard bins lw = {LW};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins lwu = {LWU};
        `endif // UDB_MXLEN_64
        `ifdef F_SUPPORTED
            wildcard bins flw = {FLW};
            wildcard bins fsw = {FSW};
        `endif // F_SUPPORTED
        `ifdef ZAAMO_SUPPORTED
            wildcard bins amoswap_w = {AMOSWAP_W};
            wildcard bins amoadd_w  = {AMOADD_W};
            wildcard bins amoand_w  = {AMOAND_W};
            wildcard bins amoor_w   = {AMOOR_W};
            wildcard bins amoxor_w  = {AMOXOR_W};
            wildcard bins amomax_w  = {AMOMAX_W};
            wildcard bins amomaxu_w = {AMOMAXU_W};
            wildcard bins amomin_w  = {AMOMIN_W};
            wildcard bins amominu_w = {AMOMINU_W};
            `ifdef ZACAS_SUPPORTED
                wildcard bins amocas_w = {AMOCAS_W};
            `endif // ZACAS_SUPPORTED
        `endif // ZAAMO_SUPPORTED
    }
    offset_4byte: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) {
        type_option.weight = 0;
        bins offsets[] = {[0:12]};
    }
    cp_zama16b_4byte: cross insn_4byte, offset_4byte;

    // ================================================================
    // 8-byte accesses (ld, sd, fld, fsd, amo*.d, amocas.d): offsets [0:8]
    // ================================================================
    insn_8byte: coverpoint ins.current.insn {
        type_option.weight = 0;
        `ifdef UDB_MXLEN_64
            wildcard bins ld = {LD};
            wildcard bins sd = {SD};
        `endif // UDB_MXLEN_64
        `ifdef D_SUPPORTED
            wildcard bins fld = {FLD};
            wildcard bins fsd = {FSD};
        `endif // D_SUPPORTED
        `ifdef ZAAMO_SUPPORTED
            `ifdef UDB_MXLEN_64
                wildcard bins amoswap_d = {AMOSWAP_D};
                wildcard bins amoadd_d  = {AMOADD_D};
                wildcard bins amoand_d  = {AMOAND_D};
                wildcard bins amoor_d   = {AMOOR_D};
                wildcard bins amoxor_d  = {AMOXOR_D};
                wildcard bins amomax_d  = {AMOMAX_D};
                wildcard bins amomaxu_d = {AMOMAXU_D};
                wildcard bins amomin_d  = {AMOMIN_D};
                wildcard bins amominu_d = {AMOMINU_D};
                `ifdef ZACAS_SUPPORTED
                    wildcard bins amocas_d = {AMOCAS_D};
                `endif // ZACAS_SUPPORTED
            `endif // UDB_MXLEN_64
        `endif // ZAAMO_SUPPORTED
    }
    offset_8byte: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) {
        type_option.weight = 0;
        bins offsets[] = {[0:8]};
    }
    cp_zama16b_8byte: cross insn_8byte, offset_8byte;

    // ================================================================
    // 16-byte accesses (flq, fsq, amocas.q): offset [0:0]
    // ================================================================
    `ifdef Q_SUPPORTED
        insn_16byte_fp: coverpoint ins.current.insn {
            type_option.weight = 0;
            wildcard bins flq = {FLQ};
            wildcard bins fsq = {FSQ};
        }
        offset_16byte_fp: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) {
            type_option.weight = 0;
            bins offsets[] = {[0:0]};
        }
        cp_zama16b_16byte_fp: cross insn_16byte_fp, offset_16byte_fp;
    `endif // Q_SUPPORTED

    `ifdef ZAAMO_SUPPORTED
        `ifdef ZACAS_SUPPORTED
            `ifdef UDB_MXLEN_64
                insn_16byte_cas: coverpoint ins.current.insn {
                    type_option.weight = 0;
                    wildcard bins amocas_q = {AMOCAS_Q};
                }
                offset_16byte_cas: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) {
                    type_option.weight = 0;
                    bins offsets[] = {[0:0]};
                }
                cp_zama16b_16byte_cas: cross insn_16byte_cas, offset_16byte_cas;
            `endif // UDB_MXLEN_64
        `endif // ZACAS_SUPPORTED
    `endif // ZAAMO_SUPPORTED

endgroup

function void zama16b_sample(int hart, int issue, ins_t ins);
    Zama16b_cg.sample(ins);
endfunction
