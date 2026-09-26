///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Hypervisor exceptions from HS, VS, U and VU modes, taken in HS-mode and VS-mode.
// Written: Sadhvi Narayanan sanarayanan@hmc.edu 5 September 2025
// Modified: David_Harris@hmc.edu 24 September 2026
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSH

// With nothing pending, WFI with hstatus.VTW = 1 traps unless the implementation lets it complete at once.
// TODO: WFI_TRAP_ON_TIMEOUT_BEHAVIOR is a proposed riscv-unified-db parameter (link the UDB issue here).
`ifdef UDB_WFI_TRAP_ON_TIMEOUT_BEHAVIOR_ALWAYS_TRAP
    `define EXCEPTIONSH_WFI_VTW
`elsif UDB_WFI_TRAP_ON_TIMEOUT_BEHAVIOR_TRAP_ON_TIMEOUT
    `define EXCEPTIONSH_WFI_VTW
`endif

covergroup ExceptionsH_cg with function sample(ins_t ins);
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
    hlvw_hlvxwu_hsvw_instr: coverpoint ins.current.insn {
        wildcard bins hlv_w   = {HLV_W};
        wildcard bins hlvx_wu = {HLVX_WU};
        wildcard bins hsv_w   = {HSV_W};
    }
    hlvw_hlvxwu_hsvw_hfencevvma_hfencegvma_instr: coverpoint ins.current.insn {
        wildcard bins hlv_w       = {HLV_W};
        wildcard bins hlvx_wu     = {HLVX_WU};
        wildcard bins hsv_w       = {HSV_W};
        wildcard bins hfence_vvma = {HFENCE_VVMA};
        wildcard bins hfence_gvma = {HFENCE_GVMA};
    }
    wfi: coverpoint ins.current.insn {
        bins wfi = {WFI};
    }
    sret: coverpoint ins.current.insn {
        bins sret = {SRET};
    }
    sfence_sinval_vma: coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
        `ifdef SVINVAL_SUPPORTED
            wildcard bins sinval_vma = {SINVAL_VMA};
        `endif
    }
    sfence_vma: coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
    }

    // CSR numbers
    vstval_htval: coverpoint ins.current.insn[31:20] {
        bins vstval = {CSR_VSTVAL};
        bins htval  = {CSR_HTVAL};
    }
    vstval: coverpoint ins.current.insn[31:20] {
        bins vstval = {CSR_VSTVAL};
    }
    stval: coverpoint ins.current.insn[31:20] {
        bins stval = {CSR_STVAL};
    }
    satp: coverpoint ins.current.insn[31:20] {
        bins satp = {CSR_SATP};
    }
    vsatp: coverpoint ins.current.insn[31:20] {
        bins vsatp = {CSR_VSATP};
    }
    hgatp: coverpoint ins.current.insn[31:20] {
        bins hgatp = {CSR_HGATP};
    }

    // Addresses
    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
        // auto fills 000 through 111
    }

    // ============================================================================
    // CSR fields
    // ============================================================================

    // medeleg as set up by BOOT_TO_SMODE: every exception but the ecalls from HS-mode and M-mode
    medeleg_delegation: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") {
        wildcard bins ones = {32'b????_????_1111_??00_1011_0101_1111_111?};
    }
    medeleg_ecall_u_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[8] {
        bins delegated = {1};
    }
    medeleg_ecall_u_vs_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[10:8] {
        wildcard bins delegated = {3'b1?1};
    }
    // Bits 16 and 20-23 are read-only 0; bit 0 is writable only when IALIGN = 32
    hedeleg_walk: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
        bins zeros              = {32'h00000000};
        `ifndef ZCA_SUPPORTED
            bins instrmisaligned = {32'h00000001};
        `endif
        bins instraccessfault   = {32'h00000002};
        bins illegalinstr       = {32'h00000004};
        bins breakpoint         = {32'h00000008};
        bins loadmisaligned     = {32'h00000010};
        bins loadaccessfault    = {32'h00000020};
        bins storemisaligned    = {32'h00000040};
        bins storeaccessfault   = {32'h00000080};
        bins ecallu             = {32'h00000100};
        wildcard bins ones      = {32'b????_????_0000_1100_1011_0001_1111_111?};
    }
    hedeleg_writable: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
        wildcard bins ones = {32'b????_????_0000_1100_1011_0001_1111_111?};
    }
    hedeleg_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
        bins disabled = {32'h00000000};
    }
    hedeleg_ecall_u_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[8] {
        bins delegated = {1};
    }
    hedeleg_ecall_u_vs_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[10:8] {
        wildcard bins not_delegated = {3'b0?0};
    }
    hstatus_spvp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "spvp") {
        bins spvp_0 = {0};
        bins spvp_1 = {1};
    }
    hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu") {
        bins hu_disabled = {0};
        bins hu_enabled  = {1};
    }
    hstatus_vtsr_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtsr") {
        bins one = {1};
    }
    hstatus_vtvm_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins one = {1};
    }
    vsstatus_sie: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sie") {
        bins off = {0};
        bins on  = {1};
    }
    mstatus_tvm_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins tvm_disabled = {0};
    }
    mstatus_tw_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw") {
        bins tw_disabled = {0};
    }
    // Written before entering VS-mode, so the trap record shows what the exception writes
    htval_htinst_nonzero: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htval", "") != 0 &&
                                      get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "htinst", "") != 0) {
        bins nonzero = {1};
    }

    // ============================================================================
    // Crosses
    // ============================================================================

    // Each exception from VS and VU modes with each hedeleg value.  Misaligned branch and jal targets are left out:
    // they trap only without Zca, and the jalr cases below cover instruction-address-misaligned delegation.
    cp_hedeleg_illegal_instruction: cross priv_mode_vs_vu, illegalops, medeleg_delegation, hedeleg_walk;
    cp_hedeleg_breakpoint:          cross priv_mode_vs_vu, ebreak, medeleg_delegation, hedeleg_walk;
    cp_hedeleg_load_misaligned:     cross priv_mode_vs_vu, loadops, adr_LSBs, medeleg_delegation, hedeleg_walk;
    cp_hedeleg_store_misaligned:    cross priv_mode_vs_vu, storeops, adr_LSBs, medeleg_delegation, hedeleg_walk;
    cp_hedeleg_ecall:               cross priv_mode_vs_vu, ecall, medeleg_delegation, hedeleg_walk;

    // Traps from HS and U ignore hedeleg, even with all of its writable bits set
    cp_hedeleg_hs_u_illegal_instruction: cross priv_mode_s_u, illegalops, medeleg_delegation, hedeleg_writable;
    cp_hedeleg_hs_u_breakpoint:          cross priv_mode_s_u, ebreak, medeleg_delegation, hedeleg_writable;
    cp_hedeleg_hs_u_load_misaligned:     cross priv_mode_s_u, loadops, adr_LSBs, medeleg_delegation, hedeleg_writable;
    cp_hedeleg_hs_u_store_misaligned:    cross priv_mode_s_u, storeops, adr_LSBs, medeleg_delegation, hedeleg_writable;
    cp_hedeleg_hs_u_ecall:               cross priv_mode_s_u, ecall, medeleg_delegation, hedeleg_writable;

    // Ecalls taken in VS-mode and HS-mode; the trap record holds the status fields they write
    cp_ecall_to_vs: cross ecall, priv_mode_vu, medeleg_ecall_u_enabled, hedeleg_ecall_u_enabled, vsstatus_sie;
    cp_ecall_to_hs: cross ecall, priv_mode_vs_u_vu, medeleg_ecall_u_vs_enabled, hedeleg_ecall_u_vs_disabled, hstatus_spvp;

    // Traps delegated to VS-mode go through vstvec, which points to a different handler than stvec
    vstvec_trap: coverpoint ins.current.insn {
        bins ecall  = {ECALL}  iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[8]);
        bins ebreak = {EBREAK} iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[3]);
    }
    vstvec_not_stvec: coverpoint (ins.prev.csr[CSR_VSTVEC] != ins.prev.csr[CSR_STVEC]) {
        bins different = {1};
    }
    cp_vstvec: cross priv_mode_vs_vu, vstvec_trap, vstvec_not_stvec {
        // An ecall from VS-mode is never delegated to VS-mode: hedeleg[10] is read-only 0
        ignore_bins vs_ecall = binsof(priv_mode_vs_vu.VS_mode) && binsof(vstvec_trap.ecall);
    }

    // Virtual-instruction exceptions from VS-mode
    cp_virtual_instr_vs_execute_hypervisor: cross priv_mode_vs, hlvw_hlvxwu_hsvw_hfencevvma_hfencegvma_instr;
    cp_virtual_instr_vs_read_vstval_htval:  cross priv_mode_vs, csrr, vstval_htval;
    cp_virtual_instr_vs_mstatus_vsatp:      cross priv_mode_vs, csrr, vsatp, mstatus_tvm_disabled;
    cp_virtual_instr_vs_mstatus_hgatp:      cross priv_mode_vs, csrr, hgatp, mstatus_tvm_disabled;
    cp_virtual_instr_vs_sret:               cross priv_mode_vs, sret, hstatus_vtsr_enabled;
    cp_virtual_instr_vs_s_vma_instr:        cross priv_mode_vs, sfence_sinval_vma, hstatus_vtvm_enabled;
    cp_virtual_instr_vs_satp:               cross priv_mode_vs, csrr, satp, hstatus_vtvm_enabled;
    `ifdef EXCEPTIONSH_WFI_VTW
        hstatus_vtw_enabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw") {
            bins one = {1};
        }
        cp_virtual_instr_vs_wfi:            cross priv_mode_vs, wfi, hstatus_vtw_enabled, mstatus_tw_disabled;
    `endif

    // Virtual-instruction exceptions from VU-mode
    cp_virtual_instr_vu_execute_h:          cross priv_mode_vu, hlvw_hlvxwu_hsvw_hfencevvma_hfencegvma_instr;
    cp_virtual_instr_vu_read_vstval_htval:  cross priv_mode_vu, csrr, vstval_htval;
    cp_virtual_instr_vu_read_stval:         cross priv_mode_vu, csrr, stval;
    cp_virtual_instr_vu_satp:               cross priv_mode_vu, csrr, satp, mstatus_tvm_disabled;
    cp_virtual_instr_vu_vsatp:              cross priv_mode_vu, csrr, vsatp, mstatus_tvm_disabled;
    cp_virtual_instr_vu_wfi:                cross priv_mode_vu, wfi, mstatus_tw_disabled;
    cp_virtual_instr_vu_sret:               cross priv_mode_vu, sret;
    cp_virtual_instr_vu_sfence_vma:         cross priv_mode_vu, sfence_vma;

    // Counter reads from VS-mode and VU-mode that hcounteren or scounteren disables while mcounteren enables them
    `ifdef ZICNTR_SUPPORTED
        instret: coverpoint ins.current.insn[31:20] {
            bins instret = {CSR_INSTRET};
        }
        mcounteren_enabled_ir: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "ir") {
            bins enabled = {1};
        }
        hcounteren_enabled_ir: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "ir") {
            bins enabled = {1};
        }
        hcounteren_disabled_ir: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "ir") {
            bins disabled = {0};
        }
        scounteren_enabled_ir: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "ir") {
            bins enabled = {1};
        }
        scounteren_disabled_ir: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "ir") {
            bins disabled = {0};
        }
        cp_virtual_instr_vs_instret:   cross priv_mode_vs, csrr, instret, hcounteren_disabled_ir, mcounteren_enabled_ir;
        cp_virtual_instr_vu_instret_1: cross priv_mode_vu, csrr, instret, hcounteren_disabled_ir, scounteren_enabled_ir, mcounteren_enabled_ir;
        cp_virtual_instr_vu_instret_2: cross priv_mode_vu, csrr, instret, hcounteren_enabled_ir, scounteren_disabled_ir, mcounteren_enabled_ir;
        `ifdef UDB_MXLEN_32
            instreth: coverpoint ins.current.insn[31:20] {
                bins instreth = {CSR_INSTRETH};
            }
            cp_virtual_instr_vs_rv32_instreth_mcounter: cross priv_mode_vs, csrr, instreth, hcounteren_disabled_ir, mcounteren_enabled_ir;
            cp_virtual_instr_vu_rv32_instreth_1: cross priv_mode_vu, csrr, instreth, hcounteren_disabled_ir, scounteren_enabled_ir, mcounteren_enabled_ir;
            cp_virtual_instr_vu_rv32_instreth_2: cross priv_mode_vu, csrr, instreth, hcounteren_enabled_ir, scounteren_disabled_ir, mcounteren_enabled_ir;
        `endif
    `endif

    // hedelegh from VS-mode and VU-mode (RV32)
    `ifdef UDB_MXLEN_32
        `ifdef SM1P13P0_OR_LATER_SUPPORTED
            hedelegh: coverpoint ins.current.insn[31:20] {
                bins hedelegh = {CSR_HEDELEGH};
            }
            cp_virtual_instr_vs_rv32_hedelegh: cross priv_mode_vs, csrr, hedelegh;
            cp_virtual_instr_vu_rv32_hedelegh: cross priv_mode_vu, csrr, hedelegh;
        `endif
    `endif

    // hlv.w, hlvx.wu and hsv.w in each mode with hstatus.HU = 0 and 1
    cp_loadstore_priv: cross priv_mode_hs_vs_u_vu, hlvw_hlvxwu_hsvw_instr, hstatus_hu;

    // Exceptions from VS-mode taken in HS-mode write htval = 0 and htinst = 0 or a transformed instruction
    cp_xtinst_illegalinstr: cross priv_mode_vs, illegal_zeros, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
    cp_xtinst_breakpoint:   cross priv_mode_vs, ebreak, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
    cp_xtinst_virtinstr:    cross priv_mode_vs, csrr, vstval, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
    cp_xtinst_ecall:        cross priv_mode_vs, ecall, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
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
        cp_xtinst_instr_misaligned: cross priv_mode_vs, jal, pc_bit_1, imm_bit_1, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
    `endif
    // Misaligned loads and stores trap only when the hart does not perform them
    `ifndef UDB_MISALIGNED_LDST
        addr_misaligned: coverpoint ({ins.current.rs1_val + ins.current.imm}[1:0] != 2'b00) {
            bins misaligned = {1};
        }
        cp_xtinst_load_misaligned:  cross priv_mode_vs, lw, addr_misaligned, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
        cp_xtinst_store_misaligned: cross priv_mode_vs, sw, addr_misaligned, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
    `endif

    `ifdef RVMODEL_ACCESS_FAULT_ADDRESS
        jalr: coverpoint ins.current.insn {
            wildcard bins jalr = {JALR};
        }
        jalr_target_bit1: coverpoint {ins.current.rs1_val + ins.current.imm}[1] {
            bins aligned    = {0};
            bins misaligned = {1};
        }
        hlv_hsv_instr: coverpoint ins.current.insn {
            wildcard bins hlv_w = {HLV_W};
            wildcard bins hsv_w = {HSV_W};
        }
        illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        // HLV and HSV have no immediate
        hlv_address_legality: coverpoint (ins.current.rs1_val & ~(64'h3)) == (`RVMODEL_ACCESS_FAULT_ADDRESS & ~(64'h3)) {
            bins legal   = {0};
            bins illegal = {1};
        }
        hlv_addr_alignment: coverpoint ins.current.rs1_val[1:0] {
            bins aligned    = {2'b00};
            bins misaligned = {2'b01};
        }
        hlv_illegal_address: coverpoint ins.current.rs1_val {
            bins illegal = {`RVMODEL_ACCESS_FAULT_ADDRESS};
        }
        hstatus_gva_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "gva") {
            bins set = {1};
        }

        cp_hedeleg_instr_misaligned_jalr: cross priv_mode_vs_vu, jalr, jalr_target_bit1, medeleg_delegation, hedeleg_walk;
        cp_hedeleg_instr_access_fault:    cross priv_mode_vs_vu, jalr, illegal_address, medeleg_delegation, hedeleg_walk;
        cp_hedeleg_load_access_fault:     cross priv_mode_vs_vu, loadops, illegal_address, medeleg_delegation, hedeleg_walk;
        cp_hedeleg_store_access_fault:    cross priv_mode_vs_vu, storeops, illegal_address, medeleg_delegation, hedeleg_walk;

        cp_hedeleg_hs_u_instr_misaligned_jalr: cross priv_mode_s_u, jalr, jalr_target_bit1, medeleg_delegation, hedeleg_writable;
        cp_hedeleg_hs_u_instr_access_fault:    cross priv_mode_s_u, jalr, illegal_address, medeleg_delegation, hedeleg_writable;
        cp_hedeleg_hs_u_load_access_fault:     cross priv_mode_s_u, loadops, illegal_address, medeleg_delegation, hedeleg_writable;
        cp_hedeleg_hs_u_store_access_fault:    cross priv_mode_s_u, storeops, illegal_address, medeleg_delegation, hedeleg_writable;

        // Highest-priority exception of hlv.w and hsv.w on legal and access-fault addresses, aligned and misaligned
        cp_priority: cross priv_mode_hs_vs_u_vu, hlv_hsv_instr, hlv_address_legality, hlv_addr_alignment, hstatus_hu;

        // An HLV or HSV fault taken into HS-mode sets hstatus.GVA
        cp_hstatus_gva: cross priv_mode_s_u, hlv_hsv_instr, hlv_illegal_address, hstatus_gva_set;

        cp_xtinst_instr_access: cross priv_mode_vs, jalr, illegal_address, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
        cp_xtinst_load_access:  cross priv_mode_vs, lw, illegal_address, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
        cp_xtinst_store_access: cross priv_mode_vs, sw, illegal_address, medeleg_delegation, hedeleg_disabled, htval_htinst_nonzero;
    `endif
endgroup

function void exceptionsh_sample(int hart, int issue, ins_t ins);
    ExceptionsH_cg.sample(ins);
endfunction
