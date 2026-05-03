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
//              Per-instruction offset ranges are restricted to [0, 16 - size] so that
//              only accesses that genuinely fit within one 16-byte window are expected.
//              Offset bins that would cause the access to cross the boundary are excluded.
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

    // ---- 1-byte loads: offsets [0:15] ----
    cp_lb_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? LB) {
        bins offsets[] = {[0:15]};
    }
    cp_lbu_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? LBU) {
        bins offsets[] = {[0:15]};
    }

    // ---- 2-byte loads: offsets [0:14] ----
    cp_lh_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? LH) {
        bins offsets[] = {[0:14]};
    }
    cp_lhu_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? LHU) {
        bins offsets[] = {[0:14]};
    }
    `ifdef COVER_ZFH
        cp_flh_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FLH) {
            bins offsets[] = {[0:14]};
        }
    `endif

    // ---- 4-byte loads: offsets [0:12] ----
    cp_lw_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? LW) {
        bins offsets[] = {[0:12]};
    }
    `ifdef XLEN64
        cp_lwu_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? LWU) {
            bins offsets[] = {[0:12]};
        }
    `endif
    `ifdef COVER_F
        cp_flw_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FLW) {
            bins offsets[] = {[0:12]};
        }
    `endif

    // ---- 8-byte loads: offsets [0:8] ----
    `ifdef XLEN64
        cp_ld_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? LD) {
            bins offsets[] = {[0:8]};
        }
    `endif
    `ifdef COVER_D
        cp_fld_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FLD) {
            bins offsets[] = {[0:8]};
        }
    `endif

    // ---- 16-byte loads: offsets [0:0] ----
    `ifdef COVER_Q
        cp_flq_load: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FLQ) {
            bins offsets[] = {[0:0]};
        }
    `endif

    // ================================================================
    // cp_zama16b_store
    // ================================================================

    // ---- 1-byte stores: offsets [0:15] ----
    cp_sb_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? SB) {
        bins offsets[] = {[0:15]};
    }

    // ---- 2-byte stores: offsets [0:14] ----
    cp_sh_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? SH) {
        bins offsets[] = {[0:14]};
    }
    `ifdef COVER_ZFH
        cp_fsh_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FSH) {
            bins offsets[] = {[0:14]};
        }
    `endif

    // ---- 4-byte stores: offsets [0:12] ----
    cp_sw_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? SW) {
        bins offsets[] = {[0:12]};
    }
    `ifdef COVER_F
        cp_fsw_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FSW) {
            bins offsets[] = {[0:12]};
        }
    `endif

    // ---- 8-byte stores: offsets [0:8] ----
    `ifdef XLEN64
        cp_sd_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? SD) {
            bins offsets[] = {[0:8]};
        }
    `endif
    `ifdef COVER_D
        cp_fsd_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FSD) {
            bins offsets[] = {[0:8]};
    }
    `endif

    // ---- 16-byte stores: offsets [0:0] ----
    `ifdef COVER_Q
        cp_fsq_store: coverpoint ((ins.current.rs1_val + ins.current.imm) & 4'hF) iff (ins.current.insn ==? FSQ) {
            bins offsets[] = {[0:0]};
        }
    `endif

    // ================================================================
    // cp_zama16b_amo
    // ================================================================
    `ifdef COVER_ZAAMO
        // ---- 1-byte AMOs (Zabha): offsets [0:15] ----
        `ifdef COVER_ZABHA
            cp_amoswap_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOSWAP_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amoadd_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOADD_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amoand_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOAND_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amoor_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOOR_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amoxor_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOXOR_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amomax_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAX_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amomaxu_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAXU_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amomin_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMIN_B) {
                bins offsets[] = {[0:15]};
            }
            cp_amominu_b_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMINU_B) {
                bins offsets[] = {[0:15]};
            }

            // ---- 2-byte AMOs (Zabha): offsets [0:14] ----
            cp_amoswap_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOSWAP_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amoadd_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOADD_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amoand_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOAND_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amoor_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOOR_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amoxor_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOXOR_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amomax_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAX_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amomaxu_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAXU_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amomin_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMIN_H) {
                bins offsets[] = {[0:14]};
            }
            cp_amominu_h_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMINU_H) {
                bins offsets[] = {[0:14]};
            }
        `endif // COVER_ZABHA

        // ---- 4-byte AMOs: offsets [0:12] ----
        cp_amoswap_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOSWAP_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amoadd_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOADD_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amoand_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOAND_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amoor_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOOR_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amoxor_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOXOR_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amomax_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAX_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amomaxu_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAXU_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amomin_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMIN_W) {
            bins offsets[] = {[0:12]};
        }
        cp_amominu_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMINU_W) {
            bins offsets[] = {[0:12]};
        }
        `ifdef COVER_ZACAS
            cp_amocas_w_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOCAS_W) {
                bins offsets[] = {[0:12]};
            }
        `endif // COVER_ZACAS

        // ---- 8-byte AMOs (RV64): offsets [0:8] ----
        `ifdef XLEN64
            cp_amoswap_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOSWAP_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amoadd_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOADD_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amoand_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOAND_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amoor_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOOR_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amoxor_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOXOR_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amomax_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAX_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amomaxu_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMAXU_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amomin_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMIN_D) {
                bins offsets[] = {[0:8]};
            }
            cp_amominu_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOMINU_D) {
                bins offsets[] = {[0:8]};
            }
            `ifdef COVER_ZACAS
                // ---- 16-byte AMO (Zacas, RV64): offsets [0:0] ----
                cp_amocas_d_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOCAS_D) {
                    bins offsets[] = {[0:8]};
                }
                cp_amocas_q_amo: coverpoint (ins.current.rs1_val & 4'hF) iff (ins.current.insn ==? AMOCAS_Q) {
                    bins offsets[] = {[0:0]};
                }
            `endif // COVER_ZACAS
        `endif // XLEN64
    `endif // COVER_ZAAMO


endgroup

function void zama16b_sample(int hart, int issue, ins_t ins);
    Zama16b_cg.sample(ins);
endfunction
