///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Hypervisor exceptions from M, HS, VS, U and VU modes, taken in M-mode.
// Written: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2026 Harvey Mudd College
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSHSM

covergroup ExceptionsHSm_cg with function sample(ins_t ins);
    option.per_instance = 0;
    `include "general/RISCV_coverage_standard_coverpoints.svh"

    // ============================================================================
    // Instructions
    // ============================================================================

    ecall: coverpoint ins.current.insn {
        bins ecall = {ECALL};
    }
    ebreak: coverpoint ins.current.insn {
        bins ebreak = {EBREAK};
    }
    illegalops: coverpoint ins.current.insn {
        bins zeros = {'0};
        bins ones  = {'1};
    }
    illegal_zeros: coverpoint ins.current.insn {
        bins zeros = {'0};
    }
    lw: coverpoint ins.current.insn {
        wildcard bins lw = {LW};
    }
    sw: coverpoint ins.current.insn {
        wildcard bins sw = {SW};
    }
    loadops: coverpoint ins.current.insn {
        wildcard bins lw  = {LW};
        wildcard bins lh  = {LH};
        wildcard bins lhu = {LHU};
        wildcard bins lb  = {LB};
        wildcard bins lbu = {LBU};
        `ifdef UDB_MXLEN_64
            wildcard bins ld  = {LD};
            wildcard bins lwu = {LWU};
        `endif
    }
    storeops: coverpoint ins.current.insn {
        wildcard bins sb = {SB};
        wildcard bins sh = {SH};
        wildcard bins sw = {SW};
        `ifdef UDB_MXLEN_64
            wildcard bins sd = {SD};
        `endif
    }
    csrr: coverpoint ins.current.insn {
        wildcard bins csrr = {CSRR};
    }
    vstval: coverpoint ins.current.insn[31:20] {
        bins vstval = {CSR_VSTVAL};
    }
    hlv_instructions: coverpoint ins.current.insn {
        wildcard bins hlv_b   = {HLV_B};
        wildcard bins hlv_bu  = {HLV_BU};
        wildcard bins hlv_h   = {HLV_H};
        wildcard bins hlv_hu  = {HLV_HU};
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_hu = {HLVX_HU};
        wildcard bins hlvx_wu = {HLVX_WU};
        `ifdef UDB_MXLEN_64
            wildcard bins hlv_wu = {HLV_WU};
            wildcard bins hlv_d  = {HLV_D};
        `endif
    }
    hsv_instructions: coverpoint ins.current.insn {
        wildcard bins hsv_b = {HSV_B};
        wildcard bins hsv_h = {HSV_H};
        wildcard bins hsv_w = {HSV_W};
        `ifdef UDB_MXLEN_64
            wildcard bins hsv_d = {HSV_D};
        `endif
    }
    hlvw_hlvxwu_hsvw_instr: coverpoint ins.current.insn {
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_wu = {HLVX_WU};
        wildcard bins hsv_w   = {HSV_W};
    }

    // Addresses
    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
        // auto fills 000 through 111
    }
    // HLV and HSV have no immediate
    hlv_adr_LSBs: coverpoint ins.current.rs1_val[2:0] {
        // auto fills 000 through 111
    }

    // ============================================================================
    // CSR fields
    // ============================================================================

    medeleg_delegation: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") {
        bins zeros = {32'h00000000};
    }
    // With medeleg = 0, hedeleg has no effect: none and all of its writable bits (bit 0 only when IALIGN = 32)
    hedeleg_none_all: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
        bins zeros         = {32'h00000000};
        wildcard bins ones = {32'b????_????_0000_1100_1011_0001_1111_111?};
    }
    hedeleg_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
        bins disabled = {32'h00000000};
    }
    hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu") {
        bins hu_disabled = {0};
        bins hu_enabled  = {1};
    }
    // Written before entering VS-mode, so the trap record shows what the exception writes
    mtval2_mtinst_nonzero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mtval2", "") != 0 &&
                                       get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mtinst", "") != 0) {
        bins nonzero = {1};
    }

    // ============================================================================
    // Crosses
    // ============================================================================

    // With medeleg = 0, each exception from VS and VU modes traps to M-mode whatever hedeleg holds
    cp_hedeleg_illegal_instruction: cross priv_mode_vs_vu, illegalops, medeleg_delegation, hedeleg_none_all;
    cp_hedeleg_breakpoint:          cross priv_mode_vs_vu, ebreak, medeleg_delegation, hedeleg_none_all;
    cp_hedeleg_load_misaligned:     cross priv_mode_vs_vu, loadops, adr_LSBs, medeleg_delegation, hedeleg_none_all;
    cp_hedeleg_store_misaligned:    cross priv_mode_vs_vu, storeops, adr_LSBs, medeleg_delegation, hedeleg_none_all;
    cp_hedeleg_ecall:               cross priv_mode_vs_vu, ecall, medeleg_delegation, hedeleg_none_all;

    // ecall and ebreak from each mode trap to M-mode; the trap record holds mstatus.MPP/MPIE/MIE and MPV/GVA
    cp_ecall_to_m:  cross priv_mode_m_hs_vs_u_vu, ecall, medeleg_delegation;
    cp_ebreak_to_m: cross priv_mode_m_hs_vs_u_vu, ebreak, medeleg_delegation;

    // Every hlv, hlvx and hsv in M-mode at each offset of a doubleword
    cp_hlv_address_misaligned: cross priv_mode_m, hlv_instructions, hlv_adr_LSBs;
    cp_hsv_address_misaligned: cross priv_mode_m, hsv_instructions, hlv_adr_LSBs;

    // hlv.w, hlvx.wu and hsv.w in M-mode with hstatus.HU = 0 and 1
    cp_loadstore_priv: cross priv_mode_m, hlvw_hlvxwu_hsvw_instr, hstatus_hu;

    // Exceptions from VS-mode taken in M-mode write mtval2 = 0 and mtinst = 0 or a transformed instruction
    cp_xtinst_illegalinstr: cross priv_mode_vs, illegal_zeros, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
    cp_xtinst_breakpoint:   cross priv_mode_vs, ebreak, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
    cp_xtinst_virtinstr:    cross priv_mode_vs, csrr, vstval, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
    cp_xtinst_ecall:        cross priv_mode_vs, ecall, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
    // Misaligned fetches trap only when IALIGN = 32
    `ifndef ZCA_SUPPORTED
        jal: coverpoint ins.current.insn {
            wildcard bins jal = {JAL};
        }
        pc_bit_1: coverpoint ins.current.pc_rdata[1] {
            bins zero = {0};
        }
        imm_bit_1: coverpoint ins.current.imm[1] {
            bins one = {1};
        }
        cp_xtinst_instr_misaligned: cross priv_mode_vs, jal, pc_bit_1, imm_bit_1, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
    `endif
    // Misaligned loads and stores trap only when the hart does not perform them
    `ifndef UDB_MISALIGNED_LDST
        addr_misaligned: coverpoint ({ins.current.rs1_val + ins.current.imm}[1:0] != 2'b00) {
            bins misaligned = {1};
        }
        cp_xtinst_load_misaligned:  cross priv_mode_vs, lw, addr_misaligned, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
        cp_xtinst_store_misaligned: cross priv_mode_vs, sw, addr_misaligned, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
    `endif

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        jalr: coverpoint ins.current.insn {
            wildcard bins jalr = {JALR};
        }
        hlv_hsv_instr: coverpoint ins.current.insn {
            wildcard bins hlv_w = {HLV_W};
            wildcard bins hsv_w = {HSV_W};
        }
        jalr_target_bit1: coverpoint {ins.current.rs1_val + ins.current.imm}[1] {
            bins aligned    = {0};
            bins misaligned = {1};
        }
        hlv_addr_alignment: coverpoint ins.current.rs1_val[1:0] {
            bins aligned    = {2'b00};
            bins misaligned = {2'b01};
        }
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        hlv_address_legality: coverpoint (ins.current.rs1_val & ~(64'h3)) == (`RVMODEL_ACCESS_FAULT_ADDRESS & ~(64'h3)) {
            bins legal   = {0};
            bins illegal = {1};
        }
        hlv_illegal_address: coverpoint ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }

        cp_hedeleg_instr_misaligned_jalr: cross priv_mode_vs_vu, jalr, jalr_target_bit1, medeleg_delegation, hedeleg_none_all;
        cp_hedeleg_instr_access_fault:    cross priv_mode_vs_vu, jalr, illegal_address, medeleg_delegation, hedeleg_none_all;
        cp_hedeleg_load_access_fault:     cross priv_mode_vs_vu, loadops, illegal_address, medeleg_delegation, hedeleg_none_all;
        cp_hedeleg_store_access_fault:    cross priv_mode_vs_vu, storeops, illegal_address, medeleg_delegation, hedeleg_none_all;

        cp_hlv_access_fault: cross priv_mode_m, hlv_instructions, hlv_illegal_address;
        cp_hsv_access_fault: cross priv_mode_m, hsv_instructions, hlv_illegal_address;

        // Highest-priority exception of hlv.w and hsv.w on legal and access-fault addresses, aligned and misaligned
        cp_priority: cross priv_mode_m, hlv_hsv_instr, hlv_address_legality, hlv_addr_alignment, hstatus_hu;

        cp_xtinst_instr_access: cross priv_mode_vs, jalr, illegal_address, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
        cp_xtinst_load_access:  cross priv_mode_vs, lw, illegal_address, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
        cp_xtinst_store_access: cross priv_mode_vs, sw, illegal_address, medeleg_delegation, hedeleg_disabled, mtval2_mtinst_nonzero;
    `endif
endgroup

function void exceptionshsm_sample(int hart, int issue, ins_t ins);
    ExceptionsHSm_cg.sample(ins);
endfunction
