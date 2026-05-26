///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smnpm (U-mode) — Machine-mode pointer masking for next lower privilege (U-mode, no S-mode).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Description:
//   Covers menvcfg.PMM configuration (PMM=00/10/11 → PMLEN=0/7/16) in M-mode
//   and its effect on U-mode memory accesses when S-mode is not present.
//   M-mode always operates in bare (PA) mode — no virtual addressing,
//   no sign-extension — so masked upper bits are always forced to zero.
//   A_masked is computed by the test generator.
//
//       PMM = 00 → PMLEN =  0  (masking disabled)
//       PMM = 10 → PMLEN =  7  (upper  7 bits ignored, bits [63:57])
//       PMM = 11 → PMLEN = 16  (upper 16 bits masked, bits [63:48])
//
//   Coverpoints:
//     cp_pmlen_masking_write  — write executed in U-mode at tagged address A;
//                               confirmed by read-back from A_masked.
//     cp_pmlen_masking_read   — read from A_masked returns the value written
//                               at A, proving the alias under active masking.
//     cp_pmlen_disabled       — PMM=00: A and A_masked resolve to different
//                               locations; read-back does not return sentinel.
//     cp_pmm_misaligned_word  — misaligned sw/lw at scratch+1, PMLEN=7,
//                               upper 7 bits = 0x00 and 0x01.
//     cp_hardware_csr_writes  — fault on illegal address in U-mode; mtval
//                               holds the correctly masked address after trap.
//     cp_pmm_uxl_clear        — hardware clears PMM when mstatus.UXL=01.
//
///////////////////////////////////////////


`define COVER_SMNPMU

`ifdef XLEN64
    `ifndef S_SUPPORTED
        covergroup SmnpmU_cg with function sample(ins_t ins);
        option.per_instance = 0;
        `include "general/RISCV_coverage_standard_coverpoints.svh"
        `include "general/RISCV_coverage_pmm_instruction_coverpoints.svh"

        pmm_active: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
            bins pmm_10_pmlen7  = {2'b10};   // PMLEN =  7, upper  7 bits masked
            bins pmm_11_pmlen16 = {2'b11};   // PMLEN = 16, upper 16 bits masked
        }
        pmm_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") {
            bins pmm_00_disabled = {2'b00};  // PMLEN = 0, no masking
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
        jalr_a_upper_bits_nonzero: coverpoint ins.current.csr[CSR_STVAL][63:48] {
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
        uxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "uxl") {
            bins uxl_01 = {2'b01};
        }
        // senvcfg.PMM must have been cleared to 00 by hardware after UXL=01.
        pmm_after_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "menvcfg", "pmm") {
            bins pmm_cleared = {2'b00};
        }
        // For hardware csr writes, we raise an exception.
        illegal_addr: coverpoint (ins.current.rs1_val + ins.current.imm)[47:0] {
        bins is_illegal_base = {`RVMODEL_ACCESS_FAULT_ADDRESS[47:0]};
        }
        // When PMLEN=16, bare mode: upper 16 bits of mtval must be zeroed
        mtval_upper_pmm11_bare: coverpoint ins.current.csr[CSR_MTVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11) {
                bins mtval_zero = {16'h0000};   // bare mode — upper 16 bits always zeroed
        }
        // When PMLEN=7, bare mode: upper 7 bits of mtval must be zeroed
        mtval_upper_pmm10_bare: coverpoint ins.current.csr[CSR_MTVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10) {
                bins mtval_zero = {7'b0000000};  // bare mode — upper 7 bits always zeroed
        }
        exception_occurred: coverpoint ins.current.csr[CSR_MCAUSE] {
        bins any_exception = {[64'h1 : 64'hFFFF_FFFF_FFFF_FFFF]};
        }


        // =======================================================================
        // cp_pmlen_masking_write
        // =======================================================================

        // ---- Base integer stores ----
        cp_pmlen_masking_write_sb: cross priv_mode_u, pmm_active, a_upper_bits, sb_insn;
        cp_pmlen_masking_write_sh: cross priv_mode_u, pmm_active, a_upper_bits, sh_insn;
        cp_pmlen_masking_write_sw: cross priv_mode_u, pmm_active, a_upper_bits, sw_insn;
        cp_pmlen_masking_write_sd: cross priv_mode_u, pmm_active, a_upper_bits, sd_insn;
        // ---- RV64A word atomics ----
        `ifdef ZAAMO_SUPPORTED
            cp_pmlen_masking_write_amoswap_w: cross priv_mode_u, pmm_active, a_upper_bits, amoswap_w_insn;
            cp_pmlen_masking_write_amoadd_w:  cross priv_mode_u, pmm_active, a_upper_bits, amoadd_w_insn;
            cp_pmlen_masking_write_amoxor_w:  cross priv_mode_u, pmm_active, a_upper_bits, amoxor_w_insn;
            cp_pmlen_masking_write_amoand_w:  cross priv_mode_u, pmm_active, a_upper_bits, amoand_w_insn;
            cp_pmlen_masking_write_amoor_w:   cross priv_mode_u, pmm_active, a_upper_bits, amoor_w_insn;
            cp_pmlen_masking_write_amomin_w:  cross priv_mode_u, pmm_active, a_upper_bits, amomin_w_insn;
            cp_pmlen_masking_write_amomax_w:  cross priv_mode_u, pmm_active, a_upper_bits, amomax_w_insn;
            cp_pmlen_masking_write_amominu_w: cross priv_mode_u, pmm_active, a_upper_bits, amominu_w_insn;
            cp_pmlen_masking_write_amomaxu_w: cross priv_mode_u, pmm_active, a_upper_bits, amomaxu_w_insn;
            // ---- RV64A double-width atomics ----
            cp_pmlen_masking_write_amoswap_d: cross priv_mode_u, pmm_active, a_upper_bits, amoswap_d_insn;
            cp_pmlen_masking_write_amoadd_d:  cross priv_mode_u, pmm_active, a_upper_bits, amoadd_d_insn;
            cp_pmlen_masking_write_amoxor_d:  cross priv_mode_u, pmm_active, a_upper_bits, amoxor_d_insn;
            cp_pmlen_masking_write_amoand_d:  cross priv_mode_u, pmm_active, a_upper_bits, amoand_d_insn;
            cp_pmlen_masking_write_amoor_d:   cross priv_mode_u, pmm_active, a_upper_bits, amoor_d_insn;
            cp_pmlen_masking_write_amomin_d:  cross priv_mode_u, pmm_active, a_upper_bits, amomin_d_insn;
            cp_pmlen_masking_write_amomax_d:  cross priv_mode_u, pmm_active, a_upper_bits, amomax_d_insn;
            cp_pmlen_masking_write_amominu_d: cross priv_mode_u, pmm_active, a_upper_bits, amominu_d_insn;
            cp_pmlen_masking_write_amomaxu_d: cross priv_mode_u, pmm_active, a_upper_bits, amomaxu_d_insn;
        `endif // ZAAMO_SUPPORTED
        // ---- Zacas ----
        `ifdef ZACAS_SUPPORTED
            cp_pmlen_masking_write_amocas_w: cross priv_mode_u, pmm_active, a_upper_bits, amocas_w_insn;
            cp_pmlen_masking_write_amocas_d: cross priv_mode_u, pmm_active, a_upper_bits, amocas_d_insn;
            cp_pmlen_masking_write_amocas_q: cross priv_mode_u, pmm_active, a_upper_bits, amocas_q_insn;
        `endif // ZACAS_SUPPORTED
        // ---- Zabha byte/halfword atomics ----
        `ifdef ZABHA_SUPPORTED
            cp_pmlen_masking_write_amoswap_b: cross priv_mode_u, pmm_active, a_upper_bits, amoswap_b_insn;
            cp_pmlen_masking_write_amoadd_b:  cross priv_mode_u, pmm_active, a_upper_bits, amoadd_b_insn;
            cp_pmlen_masking_write_amoxor_b:  cross priv_mode_u, pmm_active, a_upper_bits, amoxor_b_insn;
            cp_pmlen_masking_write_amoand_b:  cross priv_mode_u, pmm_active, a_upper_bits, amoand_b_insn;
            cp_pmlen_masking_write_amoor_b:   cross priv_mode_u, pmm_active, a_upper_bits, amoor_b_insn;
            cp_pmlen_masking_write_amomin_b:  cross priv_mode_u, pmm_active, a_upper_bits, amomin_b_insn;
            cp_pmlen_masking_write_amomax_b:  cross priv_mode_u, pmm_active, a_upper_bits, amomax_b_insn;
            cp_pmlen_masking_write_amominu_b: cross priv_mode_u, pmm_active, a_upper_bits, amominu_b_insn;
            cp_pmlen_masking_write_amomaxu_b: cross priv_mode_u, pmm_active, a_upper_bits, amomaxu_b_insn;
            cp_pmlen_masking_write_amoswap_h: cross priv_mode_u, pmm_active, a_upper_bits, amoswap_h_insn;
            cp_pmlen_masking_write_amoadd_h:  cross priv_mode_u, pmm_active, a_upper_bits, amoadd_h_insn;
            cp_pmlen_masking_write_amoxor_h:  cross priv_mode_u, pmm_active, a_upper_bits, amoxor_h_insn;
            cp_pmlen_masking_write_amoand_h:  cross priv_mode_u, pmm_active, a_upper_bits, amoand_h_insn;
            cp_pmlen_masking_write_amoor_h:   cross priv_mode_u, pmm_active, a_upper_bits, amoor_h_insn;
            cp_pmlen_masking_write_amomin_h:  cross priv_mode_u, pmm_active, a_upper_bits, amomin_h_insn;
            cp_pmlen_masking_write_amomax_h:  cross priv_mode_u, pmm_active, a_upper_bits, amomax_h_insn;
            cp_pmlen_masking_write_amominu_h: cross priv_mode_u, pmm_active, a_upper_bits, amominu_h_insn;
            cp_pmlen_masking_write_amomaxu_h: cross priv_mode_u, pmm_active, a_upper_bits, amomaxu_h_insn;
        `endif // ZABHA_SUPPORTED
        // ---- Floating-point stores ----
        `ifdef F_SUPPORTED
            cp_pmlen_masking_write_fsw: cross priv_mode_u, pmm_active, a_upper_bits, fsw_insn;
        `endif
        `ifdef D_SUPPORTED
            cp_pmlen_masking_write_fsd: cross priv_mode_u, pmm_active, a_upper_bits, fsd_insn;
        `endif
        `ifdef Q_SUPPORTED
            cp_pmlen_masking_write_fsq: cross priv_mode_u, pmm_active, a_upper_bits, fsq_insn;
        `endif
        // ---- Zca compressed stores ----
        `ifdef ZCA_SUPPORTED
            cp_pmlen_masking_write_c_sw:   cross priv_mode_u, pmm_active, a_upper_bits, c_sw_insn;
            cp_pmlen_masking_write_c_sd:   cross priv_mode_u, pmm_active, a_upper_bits, c_sd_insn;
            cp_pmlen_masking_write_c_swsp: cross priv_mode_u, pmm_active, a_upper_bits, c_swsp_insn;
            cp_pmlen_masking_write_c_sdsp: cross priv_mode_u, pmm_active, a_upper_bits, c_sdsp_insn;
        `endif
        // ---- Zcd stores ----
        `ifdef ZCD_SUPPORTED
            cp_pmlen_masking_write_c_fsdsp: cross priv_mode_u, pmm_active, a_upper_bits, c_fsdsp_insn;
        `endif
        // ---- Zicboz cache-block zero (write effect: zeroes cache line at A) ----
        `ifdef ZICBOZ_SUPPORTED
            cp_pmlen_masking_write_cbo_zero: cross priv_mode_u, pmm_active, a_upper_bits, cbo_zero_insn;
        `endif
        // ---- Zicbom cache-block maintenance (write effect: clean/flush/inval at A) ----
        `ifdef ZICBOM_SUPPORTED
            cp_pmlen_masking_write_cbo_clean: cross priv_mode_u, pmm_active, a_upper_bits, cbo_clean_insn;
            cp_pmlen_masking_write_cbo_flush: cross priv_mode_u, pmm_active, a_upper_bits, cbo_flush_insn;
            cp_pmlen_masking_write_cbo_inval: cross priv_mode_u, pmm_active, a_upper_bits, cbo_inval_insn;
        `endif
        // ---- Zicbop prefetch hints (address resolves to same cache line as A) ----
        `ifdef ZICBOP_SUPPORTED
            cp_pmlen_masking_write_prefetch_r: cross priv_mode_u, pmm_active, a_upper_bits, prefetch_r_insn;
            cp_pmlen_masking_write_prefetch_w: cross priv_mode_u, pmm_active, a_upper_bits, prefetch_w_insn;
            cp_pmlen_masking_write_prefetch_i: cross priv_mode_u, pmm_active, a_upper_bits, prefetch_i_insn;
        `endif
        // ---- Zicfiss shadow-stack instructions ----
        `ifdef ZICFISS_SUPPORTED
            cp_pmlen_masking_write_sspush:      cross priv_mode_u, pmm_active, a_upper_bits, sspush_insn;
            cp_pmlen_masking_write_c_sspush:    cross priv_mode_u, pmm_active, a_upper_bits, c_sspush_insn;
            cp_pmlen_masking_write_ssamoswap_w: cross priv_mode_u, pmm_active, a_upper_bits, ssamoswap_w_insn;
            cp_pmlen_masking_write_ssamoswap_d: cross priv_mode_u, pmm_active, a_upper_bits, ssamoswap_d_insn;
        `endif // ZICFISS_SUPPORTED
        // ---- RVV 1.0 vector load/store instructions (ZvI32b minimum) ----
        `ifdef ZVL32B_SUPPORTED
            cp_pmlen_masking_write_vse8_v:      cross priv_mode_u, pmm_active, a_upper_bits, vse8_v_insn;
            cp_pmlen_masking_write_vse16_v:     cross priv_mode_u, pmm_active, a_upper_bits, vse16_v_insn;
            cp_pmlen_masking_write_vse32_v:     cross priv_mode_u, pmm_active, a_upper_bits, vse32_v_insn;
            cp_pmlen_masking_write_vse64_v:     cross priv_mode_u, pmm_active, a_upper_bits, vse64_v_insn;
            cp_pmlen_masking_write_vsse32_v:    cross priv_mode_u, pmm_active, a_upper_bits, vsse32_v_insn;
            cp_pmlen_masking_write_vsse64_v:    cross priv_mode_u, pmm_active, a_upper_bits, vsse64_v_insn;
            cp_pmlen_masking_write_vsuxei32_v:  cross priv_mode_u, pmm_active, a_upper_bits, vsuxei32_v_insn;
            cp_pmlen_masking_write_vsuxei64_v:  cross priv_mode_u, pmm_active, a_upper_bits, vsuxei64_v_insn;
            cp_pmlen_masking_write_vsoxei32_v:  cross priv_mode_u, pmm_active, a_upper_bits, vsoxei32_v_insn;
            cp_pmlen_masking_write_vsoxei64_v:  cross priv_mode_u, pmm_active, a_upper_bits, vsoxei64_v_insn;
            cp_pmlen_masking_write_vs1r_v:      cross priv_mode_u, pmm_active, a_upper_bits, vs1r_v_insn;
            cp_pmlen_masking_write_vsseg2e32_v: cross priv_mode_u, pmm_active, a_upper_bits, vsseg2e32_v_insn;
        `endif // ZVL32B_SUPPORTED

        // =======================================================================
        // cp_pmlen_masking_read
        // =======================================================================
        // NOTE: A_masked (the read address) is computed by the test generator, not
        // sampled here.  The generator derives A_masked from A
        // by zeroing the upper PMLEN bits, so by construction
        // A_masked always has upper bits = 0x0000 (bare) depending on given PMM

        // ---- Base integer loads ----
        cp_pmlen_masking_read_lb:  cross priv_mode_u, pmm_active, lb_insn;
        cp_pmlen_masking_read_lbu: cross priv_mode_u, pmm_active, lbu_insn;
        cp_pmlen_masking_read_lh:  cross priv_mode_u, pmm_active, lh_insn;
        cp_pmlen_masking_read_lhu: cross priv_mode_u, pmm_active, lhu_insn;
        cp_pmlen_masking_read_lw:  cross priv_mode_u, pmm_active, lw_insn;
        cp_pmlen_masking_read_lwu: cross priv_mode_u, pmm_active, lwu_insn;
        cp_pmlen_masking_read_ld:  cross priv_mode_u, pmm_active, ld_insn;
        // NOTE: RV64A / Zacas / Zabha have no standalone load instructions; their
        // read-backs use base lw/ld, already covered by the crosses above.

        // ---- Floating-point loads ----
        `ifdef F_SUPPORTED
            cp_pmlen_masking_read_flw: cross priv_mode_u, pmm_active, flw_insn;
        `endif
        `ifdef D_SUPPORTED
            cp_pmlen_masking_read_fld: cross priv_mode_u, pmm_active, fld_insn;
        `endif
        `ifdef Q_SUPPORTED
            cp_pmlen_masking_read_flq: cross priv_mode_u, pmm_active, flq_insn;
        `endif
        // ---- Zca compressed loads ----
        `ifdef ZCA_SUPPORTED
            cp_pmlen_masking_read_c_lw:   cross priv_mode_u, pmm_active, c_lw_insn;
            cp_pmlen_masking_read_c_ld:   cross priv_mode_u, pmm_active, c_ld_insn;
            cp_pmlen_masking_read_c_lwsp: cross priv_mode_u, pmm_active, c_lwsp_insn;
            cp_pmlen_masking_read_c_ldsp: cross priv_mode_u, pmm_active, c_ldsp_insn;
        `endif
        `ifdef ZCD_SUPPORTED
            cp_pmlen_masking_read_c_fldsp: cross priv_mode_u, pmm_active, c_fldsp_insn;
        `endif
        // ---- Zicboz read-back: lw/ld from A returns 0 after CBO.ZERO at A_masked ----
        `ifdef ZICBOZ_SUPPORTED
            cp_pmlen_masking_read_cbo_zero_lw: cross priv_mode_u, pmm_active, lw_insn, zero_loaded;
            cp_pmlen_masking_read_cbo_zero_ld: cross priv_mode_u, pmm_active, ld_insn, zero_loaded;
        `endif
        // The Zicbom and Zicbop read-backs are already implied by the existing base load crosses — no duplication needed.
        // ---- Zicfiss shadow-stack instructions ----
        `ifdef ZICFISS_SUPPORTED
            cp_pmlen_masking_read_sspopchk:   cross priv_mode_u, pmm_active, sspopchk_insn;
            cp_pmlen_masking_read_c_sspopchk: cross priv_mode_u, pmm_active, c_sspopchk_insn;
        `endif // ZICFISS_SUPPORTED
        // ---- RVV 1.0 vector load instructions (ZvI32b minimum) ----
        `ifdef ZVL32B_SUPPORTED
            cp_pmlen_masking_read_vle8_v:      cross priv_mode_u, pmm_active, vle8_v_insn;
            cp_pmlen_masking_read_vle16_v:     cross priv_mode_u, pmm_active, vle16_v_insn;
            cp_pmlen_masking_read_vle32_v:     cross priv_mode_u, pmm_active, vle32_v_insn;
            cp_pmlen_masking_read_vle64_v:     cross priv_mode_u, pmm_active, vle64_v_insn;
            cp_pmlen_masking_read_vlse32_v:    cross priv_mode_u, pmm_active, vlse32_v_insn;
            cp_pmlen_masking_read_vlse64_v:    cross priv_mode_u, pmm_active, vlse64_v_insn;
            cp_pmlen_masking_read_vluxei32_v:  cross priv_mode_u, pmm_active, vluxei32_v_insn;
            cp_pmlen_masking_read_vluxei64_v:  cross priv_mode_u, pmm_active, vluxei64_v_insn;
            cp_pmlen_masking_read_vloxei32_v:  cross priv_mode_u, pmm_active, vloxei32_v_insn;
            cp_pmlen_masking_read_vloxei64_v:  cross priv_mode_u, pmm_active, vloxei64_v_insn;
            cp_pmlen_masking_read_vl1r_v:      cross priv_mode_u, pmm_active, vl1r_v_insn;
            cp_pmlen_masking_read_vle8ff_v:    cross priv_mode_u, pmm_active, vle8ff_v_insn;
            cp_pmlen_masking_read_vle16ff_v:   cross priv_mode_u, pmm_active, vle16ff_v_insn;
            cp_pmlen_masking_read_vle32ff_v:   cross priv_mode_u, pmm_active, vle32ff_v_insn;
            cp_pmlen_masking_read_vle64ff_v:   cross priv_mode_u, pmm_active, vle64ff_v_insn;
            cp_pmlen_masking_read_vlseg2e32_v: cross priv_mode_u, pmm_active, vlseg2e32_v_insn;
        `endif // ZVL32B_SUPPORTED

        // cp_pmlen_disabled[]
        cp_pmlen_disabled_lw: cross priv_mode_u, pmm_disabled, lw_insn;
        cp_pmlen_disabled_sw: cross priv_mode_u, a_upper_bits, pmm_disabled, sw_insn;

        // cp_pmlen_misaligned[]
        // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 0 or 1
        cp_pm_misaligned_word_write: cross priv_mode_u, pmm_active, misaligned_a_upper7, sw_insn, misaligned_addr;
        cp_pm_misaligned_word_read:  cross priv_mode_u, pmm_active, misaligned_a_upper7, lw_insn, misaligned_addr;

        // =======================================================================
        // cp_pmm_uxl_clear
        // =======================================================================
        cp_pmm_uxl_clear: cross pmm_active, uxl_rv32, pmm_after_clear;

        // =======================================================================
        // cp_hardware_csr_writes
        // =======================================================================

        // Fault crosses confirm lw/sw executed in U-mode at the illegal address.
        // Trap crosses confirm mtval holds the correctly masked address after the fault.

        // PMM=11, Bare
        cp_hardware_csr_writes_read_pmm11_bare_fault:  cross priv_mode_u, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm11_bare_fault: cross priv_mode_u, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm11_bare_trap:   cross priv_mode_m, mtval_upper_pmm11_bare, exception_occurred, lw_insn;
        cp_hardware_csr_writes_write_pmm11_bare_trap:  cross priv_mode_m, mtval_upper_pmm11_bare, exception_occurred, sw_insn;

        // PMM=10, Bare
        cp_hardware_csr_writes_read_pmm10_bare_fault:  cross priv_mode_u, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm10_bare_fault: cross priv_mode_u, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm10_bare_trap:   cross priv_mode_m, mtval_upper_pmm10_bare, exception_occurred, lw_insn;
        cp_hardware_csr_writes_write_pmm10_bare_trap:  cross priv_mode_m, mtval_upper_pmm10_bare, exception_occurred, sw_insn;

        endgroup

        function void smnpmu_sample(int hart, int issue, ins_t ins);
            SmnpmU_cg.sample(ins);
        endfunction
    `endif //S_SUPPORTED
`endif // XLEN64
