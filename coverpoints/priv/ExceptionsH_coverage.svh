///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Sadhvi Narayanan sanarayanan@hmc.edu 5 September 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0 WITH SHL-2.1
//
// Licensed under the Solderpad Hardware License v 2.1 (the “License”); you may not use this file
// except in compliance with the License, or, at your option, the Apache License version 2.0. You
// may obtain a copy of the License at
//
// https://solderpad.org/licenses/SHL-2.1/
//
// Unless required by applicable law or agreed to in writing, any work distributed under the
// License is distributed on an “AS IS” BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
// either express or implied. See the License for the specific language governing permissions
// and limitations under the License.
////////////////////////////////////////////////////////////////////////////////////////////////


// Individual cross coverage for each exception type with delegation registers

// Building block coverpoints (similar to ExceptionsM pattern)

`define COVER_EXCEPTIONSH
covergroup ExceptionsH_exceptions_cg with function sample(ins_t ins);
    option.per_instance = 0;

    // Include standard RISCV coverpoints
    `include "coverage/RISCV_coverage_standard_coverpoints.svh"
    
    // ============================================================================
    // INSTRUCTION COVERPOINTS
    // ============================================================================
    
    branch: coverpoint ins.current.insn {
        wildcard bins branch = {32'b???????_?????_?????_???_?????_1100011};
    }

    jal: coverpoint ins.current.insn {
        wildcard bins jal = {32'b????????????????????_?????_1101111};
    }

    jalr: coverpoint ins.current.insn {
        wildcard bins jalr = {32'b????????????_?????_000_?????_1100111};
    }

    loadops: coverpoint ins.current.insn {
        wildcard bins lw  = {32'b????????????_?????_010_?????_0000011};
        wildcard bins lh  = {32'b????????????_?????_001_?????_0000011};
        wildcard bins lhu = {32'b????????????_?????_101_?????_0000011};
        wildcard bins lb  = {32'b????????????_?????_000_?????_0000011};
        wildcard bins lbu = {32'b????????????_?????_100_?????_0000011};
        `ifdef XLEN64
            wildcard bins ld  = {32'b????????????_?????_011_?????_0000011};
            wildcard bins lwu = {32'b????????????_?????_110_?????_0000011};
        `endif
    }

    storeops: coverpoint ins.current.insn {
        wildcard bins sb = {32'b????????????_?????_000_?????_0100011};
        wildcard bins sh = {32'b????????????_?????_001_?????_0100011};
        wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
        `ifdef XLEN64
            wildcard bins sd = {32'b????????????_?????_011_?????_0100011};
        `endif
    }

    ecall: coverpoint ins.current.insn {
        bins ecall = {32'h00000073};
    }

    ebreak: coverpoint ins.current.insn {
        bins ebreak = {32'h00100073};
    }

    illegalops: coverpoint ins.current.insn {
        bins zeros = {'0};
        bins ones  = {'1};
    }

    hlv_hsv_instr: coverpoint ins.current.insn {
        wildcard bins hlv_w = {32'b011010000000_?????100?????_1110011};
        wildcard bins hsv_w = {32'b0110101_??????????10000000_1110011};
    }

    csrr: coverpoint ins.current.insn {
        wildcard bins csrr = {32'b????????????_00000_010_?????_1110011};
    }

    instret: coverpoint ins.current.insn[31:20] {
        wildcard bins instret_read = {12'hc02};
    }

    // ============================================================================
    // FAULT CONDITION COVERPOINTS
    // ============================================================================

    illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
        bins illegal = {`ACCESS_FAULT_ADDRESS};
    }

    adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
        // Auto fills 000 through 111 for misalignment
    }

    addr_misalignment: coverpoint (ins.current.rs1_val + ins.current.imm)[1:0] {
        bins aligned_00 = {2'b00};
        bins misaligned_01 = {2'b01};
    }

    pc_bit_1: coverpoint ins.current.pc_rdata[1] {
        bins zero = {0};
    }

    imm_bit_1: coverpoint ins.current.imm[1] {
        bins one = {'1};
    }

    // ============================================================================
    // PRIVILEGE MODE COVERPOINTS
    // ============================================================================

    // All 5 privilege modes (M/HS/VS/VU/U)
    modes: coverpoint {ins.prev.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "v")} {
        bins M_mode  = {2'b11, 1'b0};
        bins HS_mode = {2'b01, 1'b0};
        bins VS_mode = {2'b01, 1'b1};
        bins U_mode  = {2'b00, 1'b0};
        bins VU_mode = {2'b00, 1'b1};
    }

    // Previous modes for VU delegation to VS
    priv_mode_vu: coverpoint {ins.prev.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "v")} {
        bins VU_mode = {2'b00, 1'b1};
    }

    // Previous modes for delegation to HS (U, VS, VU)
    priv_mode_to_hs: coverpoint {ins.prev.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "v")} {
        bins U_mode  = {2'b00, 1'b0};
        bins VS_mode = {2'b01, 1'b1};
        bins VU_mode = {2'b00, 1'b1};
    }

    // Previous modes for delegation to M (all 5 modes)
    priv_mode_to_m: coverpoint {ins.prev.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "v")} {
        bins M_mode  = {2'b11, 1'b?};
        bins HS_mode = {2'b01, 1'b0};
        bins U_mode  = {2'b00, 1'b0};
        bins VS_mode = {2'b01, 1'b1};
        bins VU_mode = {2'b00, 1'b1};
    }

    // Previous modes for VS (VU and VS)
    priv_mode_to_vs: coverpoint {ins.prev.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "v")} {
        bins VU_mode = {2'b00, 1'b1};
        bins VS_mode = {2'b01, 1'b1};
    }

    // VS-mode only (for virtual instruction exceptions)
    priv_mode_vs: coverpoint {ins.prev.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "v")} {
        bins VS_mode = {2'b01, 1'b1};
    }

    // ============================================================================
    // DELEGATION REGISTER COVERPOINTS
    // ============================================================================

    // Machine Exception Delegation Register (medeleg)
    medeleg_delegation: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") {
        bins zeros = {32'h00000000};
        wildcard bins walking_pattern = {32'b1111_0000_1011_1111_1111_111?};
    }

    // Hypervisor Exception Delegation Register (hedeleg)
    hedeleg_delegation: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
        bins zeros = {32'h00000000};
        wildcard bins walking_pattern = {32'b1111_0000_1011_1111_1111_111?};
        bins walk_1_bit0 = {32'h00000001}; // Instruction address misaligned
        bins walk_1_bit1 = {32'h00000002}; // Instruction access fault
        bins walk_1_bit2 = {32'h00000004}; // Illegal instruction
        bins walk_1_bit3 = {32'h00000008}; // Breakpoint
        bins walk_1_bit4 = {32'h00000010}; // Load address misaligned
        bins walk_1_bit5 = {32'h00000020}; // Load access fault
        bins walk_1_bit6 = {32'h00000040}; // Store address misaligned
        bins walk_1_bit7 = {32'h00000080}; // Store access fault
        bins walk_1_bit8 = {32'h00000100}; // Environment call from U-mode
    }

    // ECALL delegation - M-mode to HS-mode (bit 8)
    medeleg_ecall_u: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[8]) {
        bins delegated = {1};
        bins not_delegated = {0};
    }

    // ECALL delegation - HS-mode to VS-mode (bit 8)
    hedeleg_ecall_u: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[8]) {
        bins delegated = {1};
        bins not_delegated = {0};
    }

    // ECALL delegation enabled from M-mode (U/VU modes)
    medeleg_ecall_enabled_u_vu: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[8]) {
        bins delegated = {1};
    }

    // ECALL delegation enabled from M-mode (VS mode)
    medeleg_ecall_enabled_vs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[10]) {
        bins delegated = {1};
    }

    // ECALL delegation disabled at HS-mode (U/VU modes)
    hedeleg_ecall_disabled_u_vu: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[8]) {
        bins not_delegated = {0};
    }

    // ECALL delegation disabled at HS-mode (VS mode)
    hedeleg_ecall_disabled_vs: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[10]) {
        bins not_delegated = {0};
    }

    // All ECALL bits disabled (no delegation to M-mode)
    medeleg_ecall_bits_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") & 32'h00000F00) {
        bins all_ecall_bits_zero = {32'h00000000};
    }

    // ECALL delegation enabled (generic)
    medeleg_ecall_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") & (1<<8)) {
        bins delegated = {1};
    }

    // ECALL from VU-mode delegated to VS-mode
    hedeleg_ecall_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") & (1<<8)) {
        bins delegated = {1};
    }

    // EBREAK bits disabled (no delegation)
    medeleg_ebreak_bits_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") >> 3) {
        bins all_ebreak_bits_zero = {32'h0};
    }

    // ============================================================================
    // VSSTATUS CSR COVERPOINTS (VS-mode traps)
    // ============================================================================

    vsstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vsstatus", "spp") {
        bins vu_mode = {0};
        bins vs_mode = {1};
    }

    vsstatus_spie_correct: coverpoint 
        (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vsstatus", "spie") == 
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vsstatus", "sie")) {
        bins spie_correct = {1};
        bins spie_incorrect = {0};
    }

    vsstatus_sie_after_trap: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "vsstatus", "sie") {
        bins sie_disabled = {0};
        bins sie_enabled = {1};
    }

    // ============================================================================
    // HSTATUS CSR COVERPOINTS (HS-mode traps)
    // ============================================================================

    hstatus_spvp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "spvp") {
        bins spvp_0 = {0};
        bins spvp_1 = {1};
    }

    hstatus_spp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "spp") {
        bins u_hs_mode = {0};
        bins vs_vu_mode = {1};
    }

    hstatus_spv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "spv") {
        bins not_virtual = {0};
        bins virtual = {1};
    }

    hstatus_gva: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "gva") {
        bins gva_invalid = {0};
        bins gva_valid = {1};
    }

    hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu") {
        bins hu_disabled = {0};
        bins hu_enabled = {1};
    }

    // ============================================================================
    // SSTATUS CSR COVERPOINTS (HS-mode traps)
    // ============================================================================

    sstatus_sie_after_trap: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstatus", "sie") {
        bins sie_disabled = {0};
        bins sie_enabled = {1};
    }

    sstatus_spie_correct: coverpoint 
        (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "sstatus", "spie") == 
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie")) {
        bins spie_correct = {1};
        bins spie_incorrect = {0};
    }

    sstatus_sie_before_trap: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sie") {
        bins sie_was_disabled = {0};
        bins sie_was_enabled = {1};
    }

    // ============================================================================
    // MSTATUS CSR COVERPOINTS (M-mode traps)
    // ============================================================================

    mstatus_mpp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mpp") {
        bins u_mode_prev = {2'b00};
        bins s_mode_prev = {2'b01};
        bins m_mode_prev = {2'b11};
    }

    mstatus_mpv: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mpv") {
        bins not_virtual = {0};
        bins virtual = {1};
    }

    mstatus_gva: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "gva") {
        bins gva_invalid = {0};
        bins gva_valid = {1};
    }

    mstatus_mpie_correct: coverpoint 
        (get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mpie") == 
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie")) {
        bins mpie_correct = {1};
        bins mpie_incorrect = {0};
    }

    mstatus_mie_after_trap: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "mstatus", "mie") {
        bins mie_disabled = {0};
        bins mie_enabled = {1};
    }

    mstatus_mie_before_trap: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "mie") {
        bins mie_was_disabled = {0};
        bins mie_was_enabled = {1};
    }

    // ============================================================================
    // TRAP VERIFICATION COVERPOINTS
    // ============================================================================

    trap_to_vs: coverpoint {ins.current.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "v")} {
        bins trapped_to_vs = {2'b01, 1'b1};
    }

    trap_to_hs: coverpoint {ins.current.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "v")} {
        bins trapped_to_hs = {2'b01, 1'b0};
    }

    trap_to_m: coverpoint ins.current.mode {
        bins trapped_to_m = {2'b11};
    }

    // ============================================================================
    // TRAP VECTOR COVERPOINTS
    // ============================================================================

    vstvec_different_from_stvec: coverpoint 
        (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstvec") != 
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "stvec")) {
        bins different_handlers = {1};
        bins same_handlers = {0};
    }

    uses_vstvec_handler: coverpoint
        (get_pc(ins.hart, ins.issue, `SAMPLE_AFTER) == 
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstvec")) {
        bins vstvec_used = {1};
        bins vstvec_not_used = {0};
    }

    not_using_stvec: coverpoint
        (get_pc(ins.hart, ins.issue, `SAMPLE_AFTER) != 
        get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "stvec")) {
        bins stvec_not_used = {1};
        bins stvec_used = {0};
    }

    // ============================================================================
    // COUNTER DELEGATION COVERPOINTS
    // ============================================================================

    h_counteren: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) {
        bins disabled = {0};
    }

    m_counteren: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren") & (1<<2)) {
        bins enabled = {1};
    }

    // ============================================================================
    // HYPERVISOR INSTRUCTION COVERPOINTS
    // ============================================================================

    hypervisor_instr: coverpoint ins.current.insn {
        wildcard bins hlv_w = {32'b011010000000?????100?????1110011};
        wildcard bins hlvx_w = {32'b011010000011?????100?????1110011};
        wildcard bins hsv_w = {32'b0110101??????????100000001110011};
        wildcard bins hfence_vvma = {32'b0010001??????????000000001110011};
        wildcard bins hfence_gvma = {32'b0110001??????????000000001110011};
    }

    hlv_instructions: coverpoint ins.current.insn {
        wildcard bins hlv_b  = {32'b011000000000?????100?????1110011};
        wildcard bins hlv_bu = {32'b011000000001?????100?????1110011};
        wildcard bins hlv_h  = {32'b011001000000?????100?????1110011};
        wildcard bins hlv_hu = {32'b011001000001?????100?????1110011};
        wildcard bins hlv_w  = {32'b011010000000?????100?????1110011};
        wildcard bins hlv_wu = {32'b011010000001?????100?????1110011};
        wildcard bins hlvx_hu = {32'b011001000011?????100?????1110011};
        wildcard bins hlvx_wu = {32'b011010000011?????100?????1110011};
        `ifdef XLEN64
            wildcard bins hlv_d = {32'b011011000000?????100?????1110011};
        `endif
    }

    hlv_instructions_three: coverpoint ins.current.insn {
        wildcard bins hlv_b  = {32'b011000000000?????100?????1110011};
        wildcard bins hlv_h  = {32'b011001000000?????100?????1110011};
        wildcard bins hlv_w  = {32'b011010000000?????100?????1110011};
        `ifdef XLEN64
            wildcard bins hlv_d = {32'b011011000000?????100?????1110011};
        `endif
    }

    hlv_hlvx_hsv_instr: coverpoint ins.current.insn {
        wildcard bins hlv_w = {32'b011010000000?????100?????1110011};
        wildcard bins hlvx_w = {32'b011010000011?????100?????1110011};
        wildcard bins hsv_w = {32'b0110101??????????100000001110011};
    }

    hfence_instructions: coverpoint ins.current.insn {
        wildcard bins sfence_vma = {32'b0001001??????????000000001110011};
        wildcard bins hfence_vvma = {32'b0010001??????????000000001110011};
        wildcard bins hfence_gvma = {32'b0110001??????????000000001110011};
    }

    wfi: coverpoint ins.current.insn {
        wildcard bins wfi = {32'b00010000010100000000000001110011};
    }

    sret: coverpoint ins.current.insn {
        bins sret = {32'b00010000001000000000000001110011};
    }

    sfence_sinval_vma: coverpoint ins.current.insn {
        wildcard bins sfence_vma = {32'b0001001??????????000000001110011};
        wildcard bins sinval_vma = {32'b0001011??????????000000001110011};
    }

    sfence_vma: coverpoint ins.current.insn {
        wildcard bins sfence_vma = {32'b0001001??????????000000001110011};
    }

    // ============================================================================
    // CSR ACCESS COVERPOINTS
    // ============================================================================

    vstval_htval: coverpoint ins.current.insn[31:20] {
        bins vstval = {12'h243};
        bins htval = {12'h643};
    }

    satp: coverpoint ins.current.insn[31:20] {
        bins satp = {12'h180};
    }

    vsatp: coverpoint ins.current.insn[31:20] {
        bins vsatp = {12'h280};
    }

    stval: coverpoint ins.current.insn[31:20] {
        bins stval = {12'h143};
    }

    csrr_vstval_read: coverpoint ins.current.insn {
        wildcard bins vstval_read = {32'b001001000011_00000_010_?????_1110011};
    }

    `ifdef RV32
    rv32_instreth: coverpoint ins.current.insn {
        wildcard bins instreth_read = {32'b11001000001000000010?????1110011};
    }

    rv32_hedelegh: coverpoint ins.current.insn {
        wildcard bins hedelegh_read = {12'h602};
    }
    `endif

    // ============================================================================
    // HSTATUS BIT COVERPOINTS (Extended)
    // ============================================================================

    hstatus_vtw: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")) {
        bins one = {1};
    }

    hstatus_vtsr: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtsr")) {
        bins one = {1};
    }

    hstatus_vtvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
        bins vtvm_disabled = {0};
        bins vtvm_enabled = {1};
    }

    hstatus_vtvm_on: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm")) {
        bins one = {1};
    }

    hstatus_gva_set: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "gva") {
        bins gva_set = {1};
    }

    hstatus_gva_clear: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "gva") {
        bins gva_clear = {0};
    }

    // ============================================================================
    // MSTATUS BIT COVERPOINTS (Extended)
    // ============================================================================

    mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
        bins tvm_disabled = {0};
        bins tvm_enabled = {1};
    }

    mstatus_tw: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw") == 0) {
        bins zero = {0};
    }

    // ============================================================================
    // COUNTER ENABLE COVERPOINTS (Extended)
    // ============================================================================

    s_counteren: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) {
        bins enabled = {1};
    }

    s_counteren_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) {
        bins disabled = {0};
    }

    h_counteren_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) {
        bins disabled = {0};
    }

    `ifdef RV32
    rv32_hcounter: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) {
        bins zero = {0};
    }

    rv32_hcounter_1: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) {
        bins one = {1};
    }

    rv32_mcounter: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren") & (1<<2)) {
        bins one = {1};
    }

    rv32_scounter: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) {
        bins one = {1};
    }

    rv32_scounter_0: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) {
        bins zero = {0};
    }
    `endif

    // ============================================================================
    // ADDRESS ALIGNMENT COVERPOINTS
    // ============================================================================

    address_lsbs: coverpoint (ins.current.rs1_val + ins.current.imm)[2:0] {
        bins addr_000 = {3'b000};
        bins addr_001 = {3'b001};
        bins addr_010 = {3'b010};
        bins addr_011 = {3'b011};
        bins addr_100 = {3'b100};
        bins addr_101 = {3'b101};
        bins addr_110 = {3'b110};
        bins addr_111 = {3'b111};
    }

    // ============================================================================
    // EXCEPTION CODE COVERPOINTS
    // ============================================================================

    virtual_instruction_exception: coverpoint ins.current.exception_code {
        bins virtual_instr_exception = {22};
    }

    instr_page_fault: coverpoint (ins.current.csr[12'h342][31:0] == 32'd12) {
        // Auto fill 0/1
    }

    load_page_fault: coverpoint (ins.current.csr[12'h342][31:0] == 32'd13) {
        // Auto fill 0/1
    }

    store_page_fault: coverpoint (ins.current.csr[12'h342][31:0] == 32'd15) {
        // Auto fill 0/1
    }

    instr_guest_page_fault: coverpoint (ins.current.csr[12'h342][31:0] == 32'd20) {
        // Auto fill 0/1
    }

    load_guest_page_fault: coverpoint (ins.current.csr[12'h342][31:0] == 32'd21) {
        // Auto fill 0/1
    }

    store_guest_page_fault: coverpoint (ins.current.csr[12'h342][31:0] == 32'd23) {
        // Auto fill 0/1
    }

    virtual_instruction: coverpoint (ins.current.csr[12'h342][31:0] == 32'd22) {
        // Auto fill 0/1
    }

    // ============================================================================
    // VIRTUAL INSTRUCTION TRIGGERS (VU MODE)
    // ============================================================================

    virtual_instr_triggers_vu: coverpoint ins.current.insn {
        // Read instret with hcounteren[2]=0, scounteren[2]=1, mcounteren[2]=1
        wildcard bins instret_read_hc0 = {32'b11000000001000000010?????1110011}
            iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) == 0 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) == 1 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren") & (1<<2)) == 1);

        // Read instret with hcounteren[2]=1, scounteren[2]=0, mcounteren[2]=1
        wildcard bins instret_read_sc0 = {32'b11000000001000000010?????1110011}
            iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) == 1 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) == 0 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren") & (1<<2)) == 1);

        // Hypervisor instructions
        wildcard bins hlv_w = {32'b011010000000?????100?????1110011};
        wildcard bins hlvx_w = {32'b011010000011?????100?????1110011};
        wildcard bins hsv_w = {32'b0110101??????????100000001110011};
        wildcard bins hfence_vvma = {32'b0010001??????????000000001110011};
        wildcard bins hfence_gvma = {32'b0110001??????????000000001110011};

        // Read vstval, htval
        wildcard bins vstval_read = {32'b001001000011_00000_010_?????_1110011};
        wildcard bins htval_read = {32'b011001000011_00000_010_?????_1110011};

        // Read stval, satp, vsatp with mstatus.TVM=0
        wildcard bins stval_read = {32'h000101000011_00000_010_?????_1110011}
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") == 0);
        wildcard bins satp_read = {32'b000110000000_00000_010_?????_1110011}
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") == 0);
        wildcard bins vsatp_read = {32'b001010000000_00000_010_?????_1110011}
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") == 0);

        // WFI with mstatus.TW=0, no interrupt firing
        bins wfi = {32'b00010000010100000000000001110011}
            iff (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw") == 0 &&
                get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mip", "pending") == 0);

        // SRET
        bins sret = {32'b00010000001000000000000001110011};

        // SFENCE.VMA
        wildcard bins sfence_vma = {32'b0001001??????????000000001110011};

        `ifdef RV32
        // Read instreth with hcounteren[2]=0, scounteren[2]=1, mcounteren[2]=1
        wildcard bins instreth_read_hc0 = {32'b11001000001000000010?????1110011}
            iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) == 0 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) == 1 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren") & (1<<2)) == 1);

        // Read instreth with hcounteren[2]=1, scounteren[2]=0, mcounteren[2]=1
        wildcard bins instreth_read_sc0 = {32'b11001000001000000010?????1110011}
            iff ((get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren") & (1<<2)) == 1 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren") & (1<<2)) == 0 &&
                (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren") & (1<<2)) == 1);

        // Read hedelegh
        wildcard bins hedelegh_read = {32'b011000010010_00000_010_?????_1110011};
        `endif
    }

    // ============================================================================
    // PRIVILEGE MODE VS DELEGATION SETTINGS
    // ============================================================================

    vs_mode: coverpoint {ins.prev.mode, get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "v")} {
        bins VS_mode = {2'b01, 1'b1};
    }

    medeleg_settings: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") {
        bins all_zero = {32'h00000000};
        bins all_one_except_m_hs_ecall = {32'hFFFFF7FF};
    }

    hedeleg_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
        bins disabled = {32'h00000000};
    }

    // ============================================================================
    // CROSS COVERAGE
    // ============================================================================

    // Exception delegation crosses
    cp_hedeleg_instr_misaligned_branch: cross branch, pc_bit_1, imm_bit_1, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_instr_misaligned_jal: cross jal, pc_bit_1, imm_bit_1, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_instr_misaligned_jalr: cross jalr, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_instr_access_fault: cross jalr, illegal_address, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_illegal_instruction: cross illegalops, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_breakpoint: cross ebreak, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_load_misaligned: cross loadops, adr_LSBs, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_load_access_fault: cross loadops, illegal_address, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_store_misaligned: cross storeops, adr_LSBs, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_store_access_fault: cross storeops, illegal_address, modes, medeleg_delegation, hedeleg_delegation;
    cp_hedeleg_ecall: cross ecall, modes, medeleg_delegation, hedeleg_delegation;

    // ECALL delegation crosses
    cp_ecall_to_vs: cross 
        ecall,
        priv_mode_vu,
        medeleg_ecall_u,
        hedeleg_ecall_u,
        vsstatus_spp,
        vsstatus_spie_correct,
        vsstatus_sie_after_trap,
        trap_to_vs;

    cp_ecall_to_hs: cross 
        ecall,
        priv_mode_to_hs,
        medeleg_ecall_enabled_u_vu,
        medeleg_ecall_enabled_vs,
        hedeleg_ecall_disabled_u_vu,
        hedeleg_ecall_disabled_vs,
        hstatus_spvp,
        hstatus_spp,
        hstatus_spv,
        hstatus_gva,
        sstatus_sie_after_trap,
        sstatus_spie_correct,
        trap_to_hs;

    cp_ecall_to_m: cross 
        ecall,
        priv_mode_to_m,
        medeleg_ecall_bits_disabled,
        mstatus_gva,
        mstatus_mpie_correct,
        mstatus_mie_after_trap,
        trap_to_m;

    cp_ebreak_to_m: cross 
        ebreak,
        priv_mode_to_m,
        medeleg_ebreak_bits_disabled,
        mstatus_gva,
        mstatus_mpie_correct,
        mstatus_mie_after_trap,
        trap_to_m;

    // Trap vector crosses
    cp_vstvec: cross 
        ecall,
        priv_mode_to_vs,
        medeleg_ecall_enabled,
        hedeleg_ecall_enabled,
        vstvec_different_from_stvec,
        not_using_stvec,
        trap_to_vs;

    // Priority crosses
    cp_priority: cross 
        hlv_hsv_instr,
        illegal_address,
        addr_misalignment,
        priv_mode_to_m,
        hstatus_hu;

    // Virtual instruction exception crosses - VS mode
    cp_virtual_instr_vs_instret: cross h_counteren, m_counteren, csrr, instret, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_execute_hypervisor: cross hypervisor_instr, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_read_vstval_hval: cross csrr, vstval_htval, virtual_instruction_exception, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_mstatus_satp: cross csrr, satp, vsatp, mstatus_tvm, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_wfi: cross wfi, hstatus_vtw, mstatus_tw, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_sret: cross sret, hstatus_vtsr, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_s_vma_instr: cross sfence_sinval_vma, hstatus_vtvm_on, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_satp: cross csrr, satp, hstatus_vtvm_on, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_rv32_instreth_mcounter: cross rv32_instreth, rv32_mcounter, rv32_hcounter, priv_mode_vs, virtual_instruction_exception;
    cp_virtual_instr_vs_rv32_hedelegh: cross csrr, rv32_hedelegh, priv_mode_vs, virtual_instruction_exception;

    // Virtual instruction exception crosses - VU mode
    cp_virtual_instr_vu_instret_1: cross csrr, instret, h_counteren, m_counteren, s_counteren, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_instret_2: cross csrr, instret, h_counteren_disabled, s_counteren_disabled, m_counteren, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_execute_h: cross hypervisor_instr, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_read_vstval_hval: cross csrr, vstval_htval, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_read_stval: cross csrr, stval, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_satp: cross csrr, satp, mstatus_tvm, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_vsatp: cross csrr, vsatp, mstatus_tvm, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_wfi: cross wfi, hstatus_vtw, mstatus_tw, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_sret: cross sret, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_sfence_vma: cross sfence_vma, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vs_rv32_instreth_1: cross rv32_instreth, rv32_hcounter, rv32_scounter, rv32_mcounter, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vs_rv32_instreth_2: cross rv32_instreth, rv32_hcounter_1, rv32_scounter_0, rv32_mcounter, priv_mode_vu, virtual_instruction_exception;
    cp_virtual_instr_vu_rv32_hedelegh: cross csrr, rv32_hedelegh, priv_mode_vu, virtual_instruction_exception;

    // Privilege mode crosses
    cp_loadstore_priv: cross 
        hlv_hlvx_hsv_instr,
        priv_mode_all,
        hstatus_hu;

    cp_hfence_priv: cross 
        hfence_instructions,
        priv_mode_to_m,
        mstatus_tvm,
        hstatus_vtvm;

    // GVA (Guest Virtual Address) crosses - GVA should be set for address-related exceptions
    cp_gva_instr_misaligned_branch: cross branch, pc_bit_1, imm_bit_1, modes, hstatus_gva_set;
    cp_gva_instr_misaligned_jal: cross jal, pc_bit_1, imm_bit_1, modes, hstatus_gva_set;
    cp_gva_instr_misaligned_jalr: cross jalr, modes, hstatus_gva_set;
    cp_gva_instr_access_fault: cross jalr, illegal_address, modes, hstatus_gva_set;
    cp_gva_instr_page_fault: cross jalr, instr_page_fault, modes, hstatus_gva_set;
    cp_gva_instr_guest_page_fault: cross jalr, instr_guest_page_fault, modes, hstatus_gva_set;
    cp_gva_load_misaligned: cross loadops, adr_LSBs, modes, hstatus_gva_set;
    cp_gva_load_access_fault: cross loadops, illegal_address, modes, hstatus_gva_set;
    cp_gva_load_page_fault: cross loadops, load_page_fault, modes, hstatus_gva_set;
    cp_gva_load_guest_page_fault: cross loadops, load_guest_page_fault, modes, hstatus_gva_set;
    cp_gva_store_misaligned: cross storeops, adr_LSBs, modes, hstatus_gva_set;
    cp_gva_store_access_fault: cross storeops, illegal_address, modes, hstatus_gva_set;
    cp_gva_store_page_fault: cross storeops, store_page_fault, modes, hstatus_gva_set;
    cp_gva_store_guest_page_fault: cross storeops, store_guest_page_fault, modes, hstatus_gva_set;
    cp_gva_breakpoint: cross ebreak, modes, hstatus_gva_set;

    // GVA should be clear for non-address-related exceptions
    cp_gva_virtual_instruction: cross virtual_instruction, modes, hstatus_gva_clear;
    cp_gva_illegal_instruction: cross illegalops, modes, hstatus_gva_clear;
    cp_gva_ecall: cross ecall, modes, hstatus_gva_clear;

    // HLV address misalignment crosses
    cp_hlv_address_misaligned: cross hlv_instructions, address_lsbs, priv_mode_m;

    // HLV access fault crosses
    cp_hlv_access_fault: cross hlv_instructions, illegal_address, priv_mode_m;

    // HSV address misalignment crosses
    cp_hsv_address_misaligned: cross hlv_instructions_three, address_lsbs, priv_mode_m;

    // HSV access fault crosses
    cp_hsv_access_fault: cross hlv_instructions_three, illegal_address, priv_mode_m;

    // HTINST/XTINST crosses - transformed instruction encoding
    cp_xtinst_instr_misaligned_1: cross jal, pc_bit_1, imm_bit_1, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_instr_misaligned_2: cross jalr, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_instr_access: cross jalr, illegal_address, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_illegalinstr: cross illegalops, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_breakpoint: cross ebreak, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_virtinstr: cross csrr_vstval_read, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_load_misaligned: cross loadops, adr_LSBs, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_load_access: cross loadops, illegal_address, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_store_misaligned: cross storeops, adr_LSBs, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_store_access: cross storeops, illegal_address, vs_mode, medeleg_settings, hedeleg_disabled;
    cp_xtinst_ecall: cross ecall, vs_mode, medeleg_settings, hedeleg_disabled;

endgroup

function void exceptionsh_sample(int hart, int issue, ins_t ins);
    ExceptionsH_exceptions_cg.sample(ins);
endfunction