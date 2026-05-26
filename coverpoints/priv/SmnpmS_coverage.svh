///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Smnpm (S-mode) — Machine-mode pointer masking for next lower privilege (S-mode).
// SPDX-License-Identifier: Apache-2.0
//
// Written: Ammarah Wakeel (UET LHR, MAY 2026), email: ammarahwakeel9@gmail.com
//
// Copyright (C) : 2026 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// Description:
//   Covers menvcfg.PMM configuration (PMM=00/10/11 → PMLEN=0/7/16) in M-mode
//   and its effect on S-mode memory accesses across all supported  modes
//   (Bare, Sv39, Sv48, Sv57).  When PMM is active, hardware strips the upper
//   PMLEN bits of the effective address before the access reaches PMP/MMU,
//   so a tagged address A and its masked form A_masked alias to the same
//   physical location.  A_masked is computed by the test generator.
//
//   Coverpoints:
//     cp_pmlen_masking_write  — write executed in S-mode at tagged address A;
//                               confirmed by read-back from A_masked.
//     cp_pmlen_masking_read   — read from A_masked returns the value written
//                               at A, proving the alias under active masking.
//     cp_pmlen_disabled       — PMM=00: A and A_masked resolve to different
//                               locations; read-back does not return sentinel.
//     cp_pmm_mxr_addr_mode    — MXR interaction: masking suppressed when MXR=1;
//                               implicit fetch (jalr) never masked regardless.
//     cp_pmm_misaligned_word  — misaligned sw/lw at scratch+1, PMLEN=7,
//                               upper 7 bits = 0x00 and 0x01.
//     cp_hardware_csr_writes  — fault on illegal address in S-mode; stval in
//                               S-mode trap handler holds the masked address.
//     cp_pmm_uxl_clear        — hardware clears PMM when sstatus.UXL=01.
//     cp_pm_csr_software      — CSR reads/writes with upper PMLEN bits set;
//                               masking must NOT be applied to CSR accesses.
//
///////////////////////////////////////////

`define COVER_SMNPMS

`ifdef XLEN64
    `ifdef S_SUPPORTED


        covergroup SmnpmS_cg with function sample(ins_t ins);
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
        // ---- MXR bit from sstatus ----
        mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mxr") {
            bins mxr_1 = {1'b1};   // MXR=1: execute-only pages readable
            bins mxr_0 = {1'b0};   // MXR=0: normal permission checks
        }
        // ---- JALR instruction ----
        jalr_insn: coverpoint ins.current.insn {
            wildcard bins jalr = {JALR};
        }
        // for CBO.ZERO readback value
        zero_loaded: coverpoint ins.current.rd_val[63:0] {
            bins zero = {64'h0000_0000_0000_0000};
        }
        uxl_rv32: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "uxl") {
            bins uxl_01 = {2'b01};
        }
        // senvcfg.PMM must have been cleared to 00 by hardware after UXL=01.
        pmm_after_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "senvcfg", "pmm") {
            bins pmm_cleared = {2'b00};
        }
        // For hardware csr writes, we raise an exception.
        illegal_addr: coverpoint (ins.current.rs1_val + ins.current.imm)[47:0] {
            bins is_illegal_base = {`RVMODEL_ACCESS_FAULT_ADDRESS[47:0]};
        }
        // When PMLEN =16  and  {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 0
        stval_upper_pmm11_va_sign_zero: coverpoint ins.current.csr[CSR_STVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  != 4'b0000  &&
            (ins.current.rs1_val + ins.current.imm)[47] == 1'b0)  {
                bins stval_zero = {16'h0000};   //  sign-bit=0 VA
        }
        // when PMLEN =16  and {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 1
        stval_upper_pmm11_va_sign_one: coverpoint ins.current.csr[CSR_STVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  != 4'b0000  &&
            (ins.current.rs1_val + ins.current.imm)[47] == 1'b1)  {
                bins stval_ones = {16'hFFFF};   // sign-bit=1 VA (Sv39/48/57)
        }
        stval_upper_pmm11_bare: coverpoint ins.current.csr[CSR_STVAL][63:48]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b11 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  == 4'b0000) {
                bins stval_zero = {16'h0000};   // bare mode
        }
        // PMM=10, Bare: sign_ext_ones impossible — upper 7 always zeroed
        stval_upper_pmm10_bare: coverpoint ins.current.csr[CSR_STVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode")  == 4'b0000) {
                bins sign_ext_zero = {7'b0000000};
        }
        // when PMLEN =7  and {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 1
        stval_upper_pmm10_va_sign_one: coverpoint ins.current.csr[CSR_STVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") != 4'b0000&&
            (ins.current.rs1_val + ins.current.imm)[56] == 1'b1) {
                bins sign_ext_ones = {7'b1111111};
        }
        // when PMLEN =7  and {{PMLEN{effective_address[XLEN-PMLEN-1]}} = 0
        stval_upper_pmm10_va_sign_zero: coverpoint ins.current.csr[CSR_STVAL][63:57]
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "menvcfg", "pmm") == 2'b10 &&
            get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "satp", "mode") != 4'b0000&&
            (ins.current.rs1_val + ins.current.imm)[56] == 1'b0) {
                bins sign_ext_zero = {7'b0000000};
        }

        // medeleg delegation witness — precondition, not a cross dimension
        medeleg_delegated: coverpoint ins.current.csr[CSR_MEDELEG][15:5] {
            // [10]=medeleg[15] [8]=medeleg[13] [2]=medeleg[7] [0]=medeleg[5]
            wildcard bins load_store_faults_delegated = {11'b1?1??????1?1};
        }
        //To check whether any exception did occur.
        exception_occurred: coverpoint ins.current.csr[CSR_SCAUSE] {
            bins any_exception = {[64'h1 : 64'hFFFF_FFFF_FFFF_FFFF]};
        }
        // ---- CSR write/read instructions ----
        csr_write_insn: coverpoint ins.current.insn {
            wildcard bins csrrw = {CSRRW};
        }
        csr_read_insn: coverpoint ins.current.insn {
            wildcard bins csrr = {CSRR};
        }
        // ---- Target CSR address (sepc, stvec, sscratch) ----
        csr_target: coverpoint ins.current.insn[31:20] { //excluding read-only csrs
            bins sepc     = {CSR_SEPC};
            //bins stvec    = {CSR_STVEC}; //// warl field has complex write restrictions and is not easy to test
            bins sscratch = {CSR_SSCRATCH};
        }

        // =======================================================================
        // cp_pmlen_masking_write
        // =======================================================================

        // ---- Base integer stores ----
        cp_pmlen_masking_write_sb: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, sb_insn;
        cp_pmlen_masking_write_sh: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, sh_insn;
        cp_pmlen_masking_write_sw: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, sw_insn;
        cp_pmlen_masking_write_sd: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, sd_insn;
        // ---- RV64A word atomics ----
        `ifdef ZAAMO_SUPPORTED
            cp_pmlen_masking_write_amoswap_w: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoswap_w_insn;
            cp_pmlen_masking_write_amoadd_w:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoadd_w_insn;
            cp_pmlen_masking_write_amoxor_w:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoxor_w_insn;
            cp_pmlen_masking_write_amoand_w:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoand_w_insn;
            cp_pmlen_masking_write_amoor_w:   cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoor_w_insn;
            cp_pmlen_masking_write_amomin_w:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomin_w_insn;
            cp_pmlen_masking_write_amomax_w:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomax_w_insn;
            cp_pmlen_masking_write_amominu_w: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amominu_w_insn;
            cp_pmlen_masking_write_amomaxu_w: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomaxu_w_insn;
            // ---- RV64A double-width atomics ----
            cp_pmlen_masking_write_amoswap_d: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoswap_d_insn;
            cp_pmlen_masking_write_amoadd_d:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoadd_d_insn;
            cp_pmlen_masking_write_amoxor_d:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoxor_d_insn;
            cp_pmlen_masking_write_amoand_d:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoand_d_insn;
            cp_pmlen_masking_write_amoor_d:   cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoor_d_insn;
            cp_pmlen_masking_write_amomin_d:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomin_d_insn;
            cp_pmlen_masking_write_amomax_d:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomax_d_insn;
            cp_pmlen_masking_write_amominu_d: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amominu_d_insn;
            cp_pmlen_masking_write_amomaxu_d: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomaxu_d_insn;
        `endif // ZAAMO_SUPPORTED
        // ---- Zacas ----
        `ifdef ZACAS_SUPPORTED
            cp_pmlen_masking_write_amocas_w: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amocas_w_insn;
            cp_pmlen_masking_write_amocas_d: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amocas_d_insn;
            cp_pmlen_masking_write_amocas_q: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amocas_q_insn;
        `endif // ZACAS_SUPPORTED
        // ---- Zabha byte/halfword atomics ----
        `ifdef ZABHA_SUPPORTED
            cp_pmlen_masking_write_amoswap_b: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoswap_b_insn;
            cp_pmlen_masking_write_amoadd_b:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoadd_b_insn;
            cp_pmlen_masking_write_amoxor_b:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoxor_b_insn;
            cp_pmlen_masking_write_amoand_b:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoand_b_insn;
            cp_pmlen_masking_write_amoor_b:   cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoor_b_insn;
            cp_pmlen_masking_write_amomin_b:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomin_b_insn;
            cp_pmlen_masking_write_amomax_b:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomax_b_insn;
            cp_pmlen_masking_write_amominu_b: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amominu_b_insn;
            cp_pmlen_masking_write_amomaxu_b: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomaxu_b_insn;
            cp_pmlen_masking_write_amoswap_h: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoswap_h_insn;
            cp_pmlen_masking_write_amoadd_h:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoadd_h_insn;
            cp_pmlen_masking_write_amoxor_h:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoxor_h_insn;
            cp_pmlen_masking_write_amoand_h:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoand_h_insn;
            cp_pmlen_masking_write_amoor_h:   cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amoor_h_insn;
            cp_pmlen_masking_write_amomin_h:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomin_h_insn;
            cp_pmlen_masking_write_amomax_h:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomax_h_insn;
            cp_pmlen_masking_write_amominu_h: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amominu_h_insn;
            cp_pmlen_masking_write_amomaxu_h: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, amomaxu_h_insn;
        `endif // ZABHA_SUPPORTED
        // ---- Floating-point stores ----
        `ifdef F_SUPPORTED
            cp_pmlen_masking_write_fsw: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, fsw_insn;
        `endif
        `ifdef D_SUPPORTED
            cp_pmlen_masking_write_fsd: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, fsd_insn;
        `endif
        `ifdef Q_SUPPORTED
            cp_pmlen_masking_write_fsq: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, fsq_insn;
        `endif
        // ---- Zca compressed stores ----
        `ifdef ZCA_SUPPORTED
            cp_pmlen_masking_write_c_sw:   cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, c_sw_insn;
            cp_pmlen_masking_write_c_sd:   cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, c_sd_insn;
            cp_pmlen_masking_write_c_swsp: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, c_swsp_insn;
            cp_pmlen_masking_write_c_sdsp: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, c_sdsp_insn;
        `endif
        // ---- Zcd stores ----
        `ifdef ZCD_SUPPORTED
            cp_pmlen_masking_write_c_fsdsp: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, c_fsdsp_insn;
        `endif
        // ---- Zicboz cache-block zero (write effect: zeroes cache line at A) ----
        `ifdef ZICBOZ_SUPPORTED
            cp_pmlen_masking_write_cbo_zero: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, cbo_zero_insn;
        `endif
        // ---- Zicbom cache-block maintenance (write effect: clean/flush/inval at A) ----
        `ifdef ZICBOM_SUPPORTED
            cp_pmlen_masking_write_cbo_clean: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, cbo_clean_insn;
            cp_pmlen_masking_write_cbo_flush: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, cbo_flush_insn;
            cp_pmlen_masking_write_cbo_inval: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, cbo_inval_insn;
        `endif
        // ---- Zicbop prefetch hints (address resolves to same cache line as A) ----
        `ifdef ZICBOP_SUPPORTED
            cp_pmlen_masking_write_prefetch_r: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, prefetch_r_insn;
            cp_pmlen_masking_write_prefetch_w: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, prefetch_w_insn;
            cp_pmlen_masking_write_prefetch_i: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, prefetch_i_insn;
        `endif
        // ---- Zicfiss shadow-stack instructions ----
        `ifdef ZICFISS_SUPPORTED
            cp_pmlen_masking_write_sspush:      cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, sspush_insn;
            cp_pmlen_masking_write_c_sspush:    cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, c_sspush_insn;
            cp_pmlen_masking_write_ssamoswap_w: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, ssamoswap_w_insn;
            cp_pmlen_masking_write_ssamoswap_d: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, ssamoswap_d_insn;
        `endif // ZICFISS_SUPPORTED
        // ---- RVV 1.0 vector load/store instructions (ZvI32b minimum) ----
        `ifdef ZVL32B_SUPPORTED
            cp_pmlen_masking_write_vse8_v:      cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vse8_v_insn;
            cp_pmlen_masking_write_vse16_v:     cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vse16_v_insn;
            cp_pmlen_masking_write_vse32_v:     cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vse32_v_insn;
            cp_pmlen_masking_write_vse64_v:     cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vse64_v_insn;
            cp_pmlen_masking_write_vsse32_v:    cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vsse32_v_insn;
            cp_pmlen_masking_write_vsse64_v:    cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vsse64_v_insn;
            cp_pmlen_masking_write_vsuxei32_v:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vsuxei32_v_insn;
            cp_pmlen_masking_write_vsuxei64_v:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vsuxei64_v_insn;
            cp_pmlen_masking_write_vsoxei32_v:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vsoxei32_v_insn;
            cp_pmlen_masking_write_vsoxei64_v:  cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vsoxei64_v_insn;
            cp_pmlen_masking_write_vs1r_v:      cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vs1r_v_insn;
            cp_pmlen_masking_write_vsseg2e32_v: cross priv_mode_s, pmm_active, satp_mode, a_upper_bits, vsseg2e32_v_insn;
        `endif // ZVL32B_SUPPORTED

        // =======================================================================
        // cp_pmlen_masking_read
        // =======================================================================
        // NOTE: A_masked (the read address) is computed by the test generator, not
        // sampled here. The generator derives A_masked from A by zeroing /
        // sign-extending the upper PMLEN bits per menvcfg.PMM and satp.MODE.

        // ---- Base integer loads ----
        cp_pmlen_masking_read_lb:  cross priv_mode_s, pmm_active, satp_mode, lb_insn;
        cp_pmlen_masking_read_lbu: cross priv_mode_s, pmm_active, satp_mode, lbu_insn;
        cp_pmlen_masking_read_lh:  cross priv_mode_s, pmm_active, satp_mode, lh_insn;
        cp_pmlen_masking_read_lhu: cross priv_mode_s, pmm_active, satp_mode, lhu_insn;
        cp_pmlen_masking_read_lw:  cross priv_mode_s, pmm_active, satp_mode, lw_insn;
        cp_pmlen_masking_read_lwu: cross priv_mode_s, pmm_active, satp_mode, lwu_insn;
        cp_pmlen_masking_read_ld:  cross priv_mode_s, pmm_active, satp_mode, ld_insn;
        // NOTE: RV64A / Zacas / Zabha have no standalone load instructions; their
        // read-backs use base lw/ld, already covered by the crosses above.

        // ---- Floating-point loads ----
        `ifdef F_SUPPORTED
            cp_pmlen_masking_read_flw: cross priv_mode_s, pmm_active, satp_mode, flw_insn;
        `endif
        `ifdef D_SUPPORTED
            cp_pmlen_masking_read_fld: cross priv_mode_s, pmm_active, satp_mode, fld_insn;
        `endif
        `ifdef Q_SUPPORTED
            cp_pmlen_masking_read_flq: cross priv_mode_s, pmm_active, satp_mode, flq_insn;
        `endif
        // ---- Zca compressed loads ----
        `ifdef ZCA_SUPPORTED
            cp_pmlen_masking_read_c_lw:   cross priv_mode_s, pmm_active, satp_mode, c_lw_insn;
            cp_pmlen_masking_read_c_ld:   cross priv_mode_s, pmm_active, satp_mode, c_ld_insn;
            cp_pmlen_masking_read_c_lwsp: cross priv_mode_s, pmm_active, satp_mode, c_lwsp_insn;
            cp_pmlen_masking_read_c_ldsp: cross priv_mode_s, pmm_active, satp_mode, c_ldsp_insn;
        `endif
        `ifdef ZCD_SUPPORTED
            cp_pmlen_masking_read_c_fldsp: cross priv_mode_s, pmm_active, satp_mode, c_fldsp_insn;
        `endif
        // ---- Zicboz read-back: lw/ld from A returns 0 after CBO.ZERO at A_masked ----
        `ifdef ZICBOZ_SUPPORTED
            cp_pmlen_masking_read_cbo_zero_lw: cross priv_mode_s, pmm_active, satp_mode, lw_insn, zero_loaded;
            cp_pmlen_masking_read_cbo_zero_ld: cross priv_mode_s, pmm_active, satp_mode, ld_insn, zero_loaded;
        `endif
        // The Zicbom and Zicbop read-backs are already implied by the existing base load crosses — no duplication needed.
        // ---- Zicfiss shadow-stack instructions ----
        `ifdef ZICFISS_SUPPORTED
            cp_pmlen_masking_read_sspopchk:   cross priv_mode_s, pmm_active, satp_mode, sspopchk_insn;
            cp_pmlen_masking_read_c_sspopchk: cross priv_mode_s, pmm_active, satp_mode, c_sspopchk_insn;
        `endif // ZICFISS_SUPPORTED
        // ---- RVV 1.0 vector load instructions (ZvI32b minimum) ----
        `ifdef ZVL32B_SUPPORTED
            cp_pmlen_masking_read_vle8_v:      cross priv_mode_s, pmm_active, satp_mode, vle8_v_insn;
            cp_pmlen_masking_read_vle16_v:     cross priv_mode_s, pmm_active, satp_mode, vle16_v_insn;
            cp_pmlen_masking_read_vle32_v:     cross priv_mode_s, pmm_active, satp_mode, vle32_v_insn;
            cp_pmlen_masking_read_vle64_v:     cross priv_mode_s, pmm_active, satp_mode, vle64_v_insn;
            cp_pmlen_masking_read_vlse32_v:    cross priv_mode_s, pmm_active, satp_mode, vlse32_v_insn;
            cp_pmlen_masking_read_vlse64_v:    cross priv_mode_s, pmm_active, satp_mode, vlse64_v_insn;
            cp_pmlen_masking_read_vluxei32_v:  cross priv_mode_s, pmm_active, satp_mode, vluxei32_v_insn;
            cp_pmlen_masking_read_vluxei64_v:  cross priv_mode_s, pmm_active, satp_mode, vluxei64_v_insn;
            cp_pmlen_masking_read_vloxei32_v:  cross priv_mode_s, pmm_active, satp_mode, vloxei32_v_insn;
            cp_pmlen_masking_read_vloxei64_v:  cross priv_mode_s, pmm_active, satp_mode, vloxei64_v_insn;
            cp_pmlen_masking_read_vl1r_v:      cross priv_mode_s, pmm_active, satp_mode, vl1r_v_insn;
            cp_pmlen_masking_read_vle8ff_v:    cross priv_mode_s, pmm_active, satp_mode, vle8ff_v_insn;
            cp_pmlen_masking_read_vle16ff_v:   cross priv_mode_s, pmm_active, satp_mode, vle16ff_v_insn;
            cp_pmlen_masking_read_vle32ff_v:   cross priv_mode_s, pmm_active, satp_mode, vle32ff_v_insn;
            cp_pmlen_masking_read_vle64ff_v:   cross priv_mode_s, pmm_active, satp_mode, vle64ff_v_insn;
            cp_pmlen_masking_read_vlseg2e32_v: cross priv_mode_s, pmm_active, satp_mode, vlseg2e32_v_insn;
        `endif // ZVL32B_SUPPORTED

        // cp_pmlen_disabled[]
        cp_pmlen_disabled_lw: cross priv_mode_s, pmm_disabled, satp_mode, lw_insn;
        cp_pmlen_disabled_sw: cross priv_mode_s, a_upper_bits, pmm_disabled, satp_mode, sw_insn;

        // cp_pmlen_misaligned[]
        // One misaligned store and one misaligned load, PMLEN=7 only, upper 7 bits = 0 or 1
        cp_pm_misaligned_word_write: cross priv_mode_s, pmm_active, misaligned_a_upper7, sw_insn, misaligned_addr;
        cp_pm_misaligned_word_read:  cross priv_mode_s, pmm_active, misaligned_a_upper7, lw_insn, misaligned_addr;

        // cp_pmm_mxr_addr_mode_write
        cp_pmm_mxr_addr_mode_write_pmm_active_mxr: cross priv_mode_s, pmm_active, mxr_bit, satp_mode, a_upper_bits, sw_insn;
        // cp_pmm_mxr_addr_mode_read
        cp_pmm_mxr_addr_mode_read_pmm_active_mxr:  cross priv_mode_s, pmm_active, mxr_bit, satp_mode, lw_insn;

        // cp_pmm_addr_mode_jalr — not guarded by S_SUPPORTED; implicit fetch is
        // never pointer-masked regardless of PMM or MXR availability.
        cp_pmm_addr_mode_jalr: cross priv_mode_s, pmm_active, a_upper_bits, mxr_bit, satp_mode, jalr_insn, jalr_a_upper_bits_nonzero;

        // =======================================================================
        // cp_hardware_csr_writes
        // =======================================================================
        // Fault crosses confirm lw/sw executed in S-mode at the illegal address.
        // Trap crosses confirm stval holds the correctly masked address in the
        // S-mode handler (medeleg must be set to delegate faults to S-mode).

        // PMM=11, Bare
        cp_hardware_csr_writes_read_pmm11_bare_fault:  cross priv_mode_s, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm11_bare_fault: cross priv_mode_s, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm11_bare_trap:   cross priv_mode_s, stval_upper_pmm11_bare, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm11_bare_trap:  cross priv_mode_s, stval_upper_pmm11_bare, exception_occurred, medeleg_delegated, sw_insn;

        // PMM=11, VA, sign bit=0
        cp_hardware_csr_writes_read_pmm11_va_sign_zero_fault:  cross priv_mode_s, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm11_va_sign_zero_fault: cross priv_mode_s, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm11_va_sign_zero_trap:   cross priv_mode_s, stval_upper_pmm11_va_sign_zero, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm11_va_sign_zero_trap:  cross priv_mode_s, stval_upper_pmm11_va_sign_zero, exception_occurred, medeleg_delegated, sw_insn;

        // PMM=11, VA, sign bit=1
        cp_hardware_csr_writes_read_pmm11_va_sign_one_fault:   cross priv_mode_s, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm11_va_sign_one_fault:  cross priv_mode_s, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm11_va_sign_one_trap:    cross priv_mode_s, stval_upper_pmm11_va_sign_one, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm11_va_sign_one_trap:   cross priv_mode_s, stval_upper_pmm11_va_sign_one, exception_occurred, medeleg_delegated, sw_insn;

        // PMM=10, Bare
        cp_hardware_csr_writes_read_pmm10_bare_fault:  cross priv_mode_s, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm10_bare_fault: cross priv_mode_s, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm10_bare_trap:   cross priv_mode_s, stval_upper_pmm10_bare, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm10_bare_trap:  cross priv_mode_s, stval_upper_pmm10_bare, exception_occurred, medeleg_delegated, sw_insn;

        // PMM=10, VA, sign bit=0
        cp_hardware_csr_writes_read_pmm10_va_sign_zero_fault:  cross priv_mode_s, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm10_va_sign_zero_fault: cross priv_mode_s, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm10_va_sign_zero_trap:   cross priv_mode_s, stval_upper_pmm10_va_sign_zero, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm10_va_sign_zero_trap:  cross priv_mode_s, stval_upper_pmm10_va_sign_zero, exception_occurred, medeleg_delegated, sw_insn;

        // PMM=10, VA, sign bit=1
        cp_hardware_csr_writes_read_pmm10_va_sign_one_fault:   cross priv_mode_s, illegal_addr, a_upper_bits, lw_insn;
        cp_hardware_csr_writes_write_pmm10_va_sign_one_fault:  cross priv_mode_s, illegal_addr, a_upper_bits, sw_insn;
        cp_hardware_csr_writes_read_pmm10_va_sign_one_trap:    cross priv_mode_s, stval_upper_pmm10_va_sign_one, exception_occurred, medeleg_delegated, lw_insn;
        cp_hardware_csr_writes_write_pmm10_va_sign_one_trap:   cross priv_mode_s, stval_upper_pmm10_va_sign_one, exception_occurred, medeleg_delegated, sw_insn;

        // =======================================================================
        // cp_pm_csr_software_access_write / cp_pm_csr_software_access_read
        // =======================================================================
        // Pointer masking must NOT be applied to software CSR reads/writes.

        cp_pm_csr_software_access_write: cross priv_mode_s, pmm_active, csr_target, csr_write_insn;
        cp_pm_csr_software_access_read:  cross priv_mode_s, pmm_active, csr_target, csr_read_insn;

        endgroup

        function void smnpms_sample(int hart, int issue, ins_t ins);
            SmnpmS_cg.sample(ins);
        endfunction
    `endif //S_SUPPORTED
`endif // XLEN64
