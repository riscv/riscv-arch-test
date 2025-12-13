///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
//
// Written: Sadhvi Narayanan sanarayanan@hmc.edu 5 September 2025
//
// Copyright (C) 2024 Harvey Mudd College, 10x Engineers, UET Lahore, Habib University
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_EXCEPTIONSH
covergroup ExceptionsH_exceptions_cg with function sample(ins_t ins);
   option.per_instance = 0;

   // Include standard RISCV coverpoints
   `include "general/RISCV_coverage_standard_coverpoints.svh"

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


   loadop: coverpoint ins.current.insn {
       wildcard bins lw  = {32'b????????????_?????_010_?????_0000011};
   }


   storeops: coverpoint ins.current.insn {
       wildcard bins sb = {32'b????????????_?????_000_?????_0100011};
       wildcard bins sh = {32'b????????????_?????_001_?????_0100011};
       wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
       `ifdef XLEN64
           wildcard bins sd = {32'b????????????_?????_011_?????_0100011};
       `endif
   }


   storeop: coverpoint ins.current.insn {
       wildcard bins sw = {32'b????????????_?????_010_?????_0100011};
   }


   ecall: coverpoint ins.current.insn {
       bins ecall = {32'h00000073};
   }


   ebreak: coverpoint ins.current.insn {
       bins ebreak = {32'h00100073};
   }


   illegalops: coverpoint ins.current.insn {
       bins zeros = {0};
       bins ones  = {'1};
   }


   hlv_hsv_instr: coverpoint ins.current.insn {
       wildcard bins hlv_w = {32'b0110100_00000_?????_100_?????_1110011};
       wildcard bins hsv_w = {32'b0110101_?????_?????_100_00000_1110011};
   }


   csrr: coverpoint ins.current.insn {
       wildcard bins csrr = {32'b????????????_00000_010_?????_1110011};
   }


   instret: coverpoint ins.current.insn[31:20] {
        bins instret_read = {12'hc02};
   }


   instreth: coverpoint ins.current.insn[31:20] {
        bins instret_read = {12'hc82};
   }


   // ============================================================================
   // FAULT CONDITION COVERPOINTS
   // ============================================================================

   illegal_address: coverpoint ins.current.imm + ins.current.rs1_val {
       bins illegal = {`ACCESS_FAULT_ADDRESS};
   }


   address_legality: coverpoint ((ins.current.imm + ins.current.rs1_val) & ~32'h3) == (`ACCESS_FAULT_ADDRESS & ~32'h3) {
        bins legal = {0};
        bins illegal = {1};
    }


   adr_LSBs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
       // Auto fills 000 through 111 for misalignment
   }


   addr_alignment: coverpoint {ins.current.rs1_val + ins.current.imm}[1:0] {
       bins aligned_00 = {2'b00};
       bins misaligned_01 = {2'b01};
   }


   addr_misaligned: coverpoint ({ins.current.rs1_val + ins.current.imm}[1:0] != 2'b00) {
        bins misaligned = {1};
    }


   pc_bit_1: coverpoint ins.current.pc_rdata[1] {
       bins zero = {0};
   }


   imm_bit_1: coverpoint ins.current.imm[1] {
       bins one = {1};
   }


   // ============================================================================
   // PRIVILEGE MODE COVERPOINTS
   // ============================================================================

   // All 5 privilege modes (M/HS/VS/VU/U)
   priv_modes_m_hs_vs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
       bins M_mode  = {3'b011};
       bins HS_mode = {3'b001};
       bins VS_mode = {3'b101};
       bins U_mode  = {3'b000};
       bins VU_mode = {3'b100};
   }


   // VU priv modes
   priv_mode_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
       bins VU_mode = {3'b100};
   }


   // VS-mode only (for virtual instruction exceptions)
   priv_mode_vs: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
       bins VS_mode = {3'b101};
   }


   // VS/VU priv modes
   priv_mode_vs_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
       bins VS_mode = {3'b101};
       bins VU_mode = {3'b100};
   }


   // VS/U/VU priv modes
   priv_mode_vs_u_vu: coverpoint {ins.prev.mode_virt, ins.prev.mode} {
       bins VS_mode = {3'b101};
       bins U_mode  = {3'b000};
       bins VU_mode = {3'b100};
   }


   // ============================================================================
   // DELEGATION REGISTER COVERPOINTS
   // ============================================================================

   // Machine Exception Delegation Register (medeleg)
   medeleg_delegation: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") {
       bins zeros = {32'h00000000};
       wildcard bins ones = {32'b????_????_1111_??10_1111_0111_1111_111?};
   }


   // Hypervisor Exception Delegation Register (hedeleg)
   hedeleg_delegation: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
       bins zeros = {32'h00000000};
       wildcard bins ones = {32'b0000_11?0_1?11_0001_1111_111?};
       `ifdef ZICCLSM_SUPPORTED
            bins walk_1_bit0 = {32'h00000001}; // Instruction address misaligned
       `endif
       bins walk_1_bit1 = {32'h00000002}; // Instruction access fault
       bins walk_1_bit2 = {32'h00000004}; // Illegal instruction
       bins walk_1_bit3 = {32'h00000008}; // Breakpoint
       bins walk_1_bit4 = {32'h00000010}; // Load address misaligned
       bins walk_1_bit5 = {32'h00000020}; // Load access fault
       bins walk_1_bit6 = {32'h00000040}; // Store address misaligned
       bins walk_1_bit7 = {32'h00000080}; // Store access fault
       bins walk_1_bit8 = {32'h00000100}; // Environment call from U-mode
   }


   // U-mode ECALL delegation enabled: M-mode → HS-mode (medeleg bit 8)
   medeleg_ecall_u_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[8]) {
       bins delegated = {1};
   }


   // U-mode and VS-mode ECALL delegation enabled: M-mode → HS-mode (medeleg bits 8, 10)
   medeleg_ecall_u_vs_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[10:8]) {
       wildcard bins delegated = {3'b1?1};
   }


   // All ECALL bits disabled (no delegation to M-mode)
   medeleg_ecall_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[11:8]) {
       bins all_ecall_bits_zero = {4'b0000};
   }


   // EBREAK delegation disabled in medeleg (bit 3)
   medeleg_ebreak_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg")[3]) {
       bins ebreak_not_delegated = {32'h0};
   }

   // All medeleg bits 0 or 1 (except M/HS-mode ECALL bits 11, 9)
   medeleg_except_ecall: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "medeleg", "deleg") {
       bins all_zero = {32'h00000000};
       wildcard bins all_one_except_m_hs_ecall = {32'b????_????_1111_??10_1111_0101_1111_111?};
   }


   // VU-mode ECALL delegation enabled: HS-mode → VS-mode (hedeleg bit 8)
   hedeleg_ecall_u_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[8]) {
       bins delegated = {1};
   }


   // VU-mode and VS-mode ECALL delegation enabled in hedeleg (bits 8, 10)
   hedeleg_ecall_u_vs_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[10:8]) {
       wildcard bins not_delegated = {3'b1?1};
   }


   // VU-mode and VS-mode ECALL delegation disabled in hedeleg (bits 8, 10)
   hedeleg_ecall_u_vs_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg")[10:8]) {
       wildcard bins not_delegated = {3'b0?0};
   }


   hedeleg_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hedeleg", "deleg") {
       bins disabled = {32'h00000000};
   }

   // ============================================================================
   // HSTATUS CSR COVERPOINTS (HS-mode traps)
   // ============================================================================

   // Sample Supervisor previous virtual privilege to check which privilege mode we came from
   hstatus_spvp: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_AFTER, "hstatus", "spvp") {
       bins spvp_0 = {0};
       bins spvp_1 = {1};
   }


   // Sample before to check if hypervisor memory access from U-mode was enabled
   hstatus_hu: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "hu") {
       bins hu_disabled = {0};
       bins hu_enabled = {1};
   }


   // ============================================================================
   // TRAP VECTOR COVERPOINTS
   // ============================================================================


   vstvec_different_from_stvec: coverpoint
       {get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "vstvec", "mode") !=
       get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "stvec", "mode")} {
       bins different_handlers = {1};
   }


   // ============================================================================
   // COUNTER DELEGATION COVERPOINTS
   // ============================================================================

   hcounteren_disabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren")[2]) {
       bins disabled = {0};
   }


   mcounteren_enabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren")[2]) {
       bins enabled = {1};
   }


   // ============================================================================
   // HYPERVISOR INSTRUCTION COVERPOINTS
   // ============================================================================

   hlvw_hlvxwu_hsvw_hfencevvma_hfencegvma_instr: coverpoint ins.current.insn {
       wildcard bins hlv_w = {32'b011010000000?????100?????1110011};
       wildcard bins hlvx_wu = {32'b011010000011?????100?????1110011};
       wildcard bins hsv_w = {32'b0110101_??????????_100_00000_1110011};
       wildcard bins hfence_vvma = {32'b0010001??????????000000001110011};
       wildcard bins hfence_gvma = {32'b0110001??????????000000001110011};
   }


   hlv_instructions: coverpoint ins.current.insn {
       wildcard bins hlv_b  = {32'b011000000000?????100?????1110011};
       wildcard bins hlv_bu = {32'b011000000001?????100?????1110011};
       wildcard bins hlv_h  = {32'b011001000000?????100?????1110011};
       wildcard bins hlv_hu = {32'b011001000001?????100?????1110011};
       wildcard bins hlv_w  = {32'b011010000000?????100?????1110011};
       wildcard bins hlvx_hu = {32'b011001000011?????100?????1110011};
       wildcard bins hlvx_wu = {32'b011010000011?????100?????1110011};
       `ifdef XLEN64
           wildcard bins hlv_d = {32'b011011000000?????100?????1110011};
           wildcard bins hlv_wu = {32'b011010000001?????100?????1110011};
       `endif
   }


   hlvb_hlvh_hlvw_hlvd_instructions: coverpoint ins.current.insn {
       wildcard bins hlv_b  = {32'b011000000000?????100?????1110011};
       wildcard bins hlv_h  = {32'b011001000000?????100?????1110011};
       wildcard bins hlv_w  = {32'b011010000000?????100?????1110011};
       `ifdef XLEN64
           wildcard bins hlv_d = {32'b011011000000?????100?????1110011};
       `endif
   }


   hsvb_hsvh_hsvw_instructions: coverpoint ins.current.insn {
       wildcard bins hsv_b  = {32'b0110001??????????100000001110011};
       wildcard bins hsv_h  = {32'b0110011??????????100000001110011};
       wildcard bins hsv_w  = {32'b0110101??????????100000001110011};
       `ifdef XLEN64
           wildcard bins hsv_d = {2'b0110111??????????100000001110011};
       `endif
   }


   hlv_hlvx_hsv_instr: coverpoint ins.current.insn {
       wildcard bins hlv_w = {32'b011010000000?????100?????1110011};
       wildcard bins hlvx_w = {32'b011010000011?????100?????1110011};
       wildcard bins hsv_w = {32'b0110101_?????_?????_100_00000_1110011};
   }


   sfencevma_hfencevvma_hfencegvma_instr: coverpoint ins.current.insn {
       wildcard bins sfence_vma = {32'b0001001??????????000000001110011};
       wildcard bins hfence_vvma = {32'b0010001??????????000000001110011};
       wildcard bins hfence_gvma = {32'b0110001??????????000000001110011};
   }


   wfi: coverpoint ins.current.insn {
        bins wfi = {32'b00010000010100000000000001110011};
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

   vstval: coverpoint ins.current.insn[31:20] {
       bins vstval = {12'h243};
   }

   `ifdef XLEN32
        rv32_hedelegh: coverpoint ins.current.insn[31:20] {
                bins hedelegh_read = {12'h602};
        }
   `endif


   // ============================================================================
   // HSTATUS BIT COVERPOINTS
   // ============================================================================

   hstatus_vtw_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtw")) {
       bins one = {1};
   }


   hstatus_vtsr_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtsr")) {
       bins one = {1};
   }


   hstatus_vtvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm") {
       bins vtvm_disabled = {0};
       bins vtvm_enabled = {1};
   }


   hstatus_vtvm_enabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hstatus", "vtvm")) {
       bins one = {1};
   }


   // ============================================================================
   // MSTATUS BIT COVERPOINTS
   // ============================================================================

   mstatus_tvm_disabled: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
       bins tvm_disabled = {0};
   }


   mstatus_tvm: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tvm") {
       bins tvm_disabled = {0};
       bins tvm_enabled = {0};
   }


   mstatus_tw_disabled: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mstatus", "tw") == 0) {
       bins zero = {0};
   }


   // ============================================================================
   // COUNTER ENABLE COVERPOINTS
   // ============================================================================

   scounteren_enabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren")[2]) {
       bins enabled = {1};
   }


   scounteren_disabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren")[2]) {
       bins disabled = {0};
   }


   hcounteren_enabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren")[2]) {
       bins enabled = {1};
   }


   `ifdef XLEN32
        rv32_hcounter_disabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren")[2]) {
            bins zero = {0};
        }


        rv32_hcounter_enabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "hcounteren", "counteren")[2]) {
            bins one = {1};
        }


        rv32_mcounter_enabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "mcounteren", "counteren")[2]) {
            bins one = {1};
        }


        rv32_scounter_enabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren")[2]) {
            bins one = {1};
        }


        rv32_scounter_disabled_ir: coverpoint (get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "scounteren", "counteren")[2]) {
            bins zero = {0};
        }
   `endif


   // ============================================================================
   // ADDRESS ALIGNMENT COVERPOINTS
   // ============================================================================

   address_lsbs: coverpoint {ins.current.rs1_val + ins.current.imm}[2:0] {
   }


   // ============================================================================
   // EXCEPTION CODE COVERPOINTS
   // ============================================================================

   instr_page_fault: coverpoint {ins.current.csr[12'h342][31:0] == 32'd12} {
       // Auto fill 0/1
   }


   load_page_fault: coverpoint {ins.current.csr[12'h342][31:0] == 32'd13} {
       // Auto fill 0/1
   }


   store_page_fault: coverpoint {ins.current.csr[12'h342][31:0] == 32'd15} {
       // Auto fill 0/1
   }


   instr_guest_page_fault: coverpoint {ins.current.csr[12'h342][31:0] == 32'd20} {
       // Auto fill 0/1
   }


   load_guest_page_fault: coverpoint {ins.current.csr[12'h342][31:0] == 32'd21} {
       // Auto fill 0/1
   }


   store_guest_page_fault: coverpoint {ins.current.csr[12'h342][31:0] == 32'd23} {
       // Auto fill 0/1
   }


   virtual_instruction: coverpoint {ins.current.csr[12'h342][31:0] == 32'd22} {
       // Auto fill 0/1
   }


   // ============================================================================
   // CROSS COVERAGE
   // ============================================================================

   // cp_hedeleg crosses
   cp_hedeleg_instr_access_fault: cross jalr, illegal_address, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_load_access_fault: cross loadop, illegal_address, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_store_access_fault: cross storeop, illegal_address, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_instr_misaligned_branch: cross branch, pc_bit_1, imm_bit_1, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_instr_misaligned_jal: cross jal, pc_bit_1, imm_bit_1, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_instr_misaligned_jalr: cross jalr, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_load_misaligned: cross loadop, adr_LSBs, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_store_misaligned: cross storeop, adr_LSBs, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_illegal_instruction: cross illegalops, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;
   cp_hedeleg_breakpoint: cross ebreak, priv_modes_m_hs_vs_u_vu, medeleg_delegation, hedeleg_delegation;


   // ECALL delegation crosses
   cp_ecall_to_vs: cross
       ecall,
       priv_mode_vu,
       medeleg_ecall_u_enabled,
       hedeleg_ecall_u_enabled;


   cp_ecall_to_hs: cross
       ecall,
       priv_mode_vs_u_vu,
       medeleg_ecall_u_vs_enabled,
       hedeleg_ecall_u_vs_disabled,
       hstatus_spvp;


   cp_ecall_to_m: cross
       ecall,
       priv_modes_m_hs_vs_u_vu,
       medeleg_ecall_disabled;


   cp_ebreak_to_m: cross
       ebreak,
       priv_modes_m_hs_vs_u_vu,
       medeleg_ebreak_disabled;


   // Trap vector crosses
   cp_vstvec: cross
       ecall,
       priv_mode_vs_vu,
       medeleg_ecall_u_vs_enabled,
       hedeleg_ecall_u_vs_enabled,
       vstvec_different_from_stvec;


   // Priority crosses
   // checking for legal addresses is not as rigorous right now
   cp_priority: cross
       hlv_hsv_instr,
       address_legality,
       addr_alignment,
       priv_modes_m_hs_vs_u_vu,
       hstatus_hu;


   // Virtual instruction exception crosses - VS mode
   cp_virtual_instr_vs_instret: cross hcounteren_disabled_ir, mcounteren_enabled_ir, csrr, instret, priv_mode_vs;
   cp_virtual_instr_vs_execute_hypervisor: cross hlvw_hlvxwu_hsvw_hfencevvma_hfencegvma_instr, priv_mode_vs;
   cp_virtual_instr_vs_read_vstval_hval: cross csrr, vstval_htval, priv_mode_vs;
   cp_virtual_instr_vs_mstatus_satp: cross csrr, satp, mstatus_tvm_disabled, priv_mode_vs;
   cp_virtual_instr_vs_mstatus_vsatp: cross csrr, vsatp, mstatus_tvm_disabled, priv_mode_vs;
   cp_virtual_instr_vs_wfi: cross wfi, hstatus_vtw_enabled, mstatus_tw_disabled, priv_mode_vs;
   cp_virtual_instr_vs_sret: cross sret, hstatus_vtsr_enabled, priv_mode_vs;
   cp_virtual_instr_vs_s_vma_instr: cross sfence_sinval_vma, hstatus_vtvm_enabled, priv_mode_vs;
   cp_virtual_instr_vs_satp: cross csrr, satp, hstatus_vtvm_enabled, priv_mode_vs;
   `ifdef XLEN32
       cp_virtual_instr_vs_rv32_instreth_mcounter: cross csrr, instreth, rv32_mcounter_enabled_ir, rv32_hcounter_disabled_ir, priv_mode_vs;
       cp_virtual_instr_vs_rv32_hedelegh: cross csrr, rv32_hedelegh, priv_mode_vs;
   `endif


   // Virtual instruction exception crosses - VU mode
   cp_virtual_instr_vu_instret_1: cross csrr, instret, hcounteren_disabled_ir, mcounteren_enabled_ir, scounteren_enabled_ir, priv_mode_vu;
   cp_virtual_instr_vu_instret_2: cross csrr, instret, hcounteren_enabled_ir, scounteren_disabled_ir, mcounteren_enabled_ir, priv_mode_vu;
   cp_virtual_instr_vu_execute_h: cross hlvw_hlvxwu_hsvw_hfencevvma_hfencegvma_instr, priv_mode_vu;
   cp_virtual_instr_vu_read_vstval_hval: cross csrr, vstval_htval, priv_mode_vu;
   cp_virtual_instr_vu_read_stval: cross csrr, stval, priv_mode_vu;
   cp_virtual_instr_vu_satp: cross csrr, satp, mstatus_tvm_disabled, priv_mode_vu;
   cp_virtual_instr_vu_vsatp: cross csrr, vsatp, mstatus_tvm_disabled, priv_mode_vu;
   cp_virtual_instr_vu_wfi: cross wfi, mstatus_tw_disabled, priv_mode_vu;
   cp_virtual_instr_vu_sret: cross sret, priv_mode_vu;
   cp_virtual_instr_vu_sfence_vma: cross sfence_vma, priv_mode_vu;
   `ifdef XLEN32
       cp_virtual_instr_vu_rv32_instreth_1: cross csrr, instreth, rv32_hcounter_disabled_ir, rv32_scounter_enabled_ir, rv32_mcounter_enabled_ir, priv_mode_vu;
       cp_virtual_instr_vu_rv32_instreth_2: cross csrr, instreth, rv32_hcounter_enabled_ir, rv32_scounter_disabled_ir, rv32_mcounter_enabled_ir, priv_mode_vu;
       cp_virtual_instr_vu_rv32_hedelegh: cross csrr, rv32_hedelegh, priv_mode_vu;
   `endif


   // Privilege mode crosses
   cp_loadstore_priv: cross
       hlv_hlvx_hsv_instr,
       priv_modes_m_hs_vs_u_vu,
       hstatus_hu;


   cp_hfence_priv: cross
       sfencevma_hfencevvma_hfencegvma_instr,
       priv_modes_m_hs_vs_u_vu,
       mstatus_tvm,
       hstatus_vtvm;


   // HLV address misalignment crosses
   cp_hlv_address_misaligned: cross hlv_instructions, address_lsbs, priv_mode_m;


   // HLV access fault crosses
   cp_hlv_access_fault: cross hlv_instructions, illegal_address, priv_mode_m;


   // HSV address misalignment crosses
   cp_hsv_address_misaligned: cross hsvb_hsvh_hsvw_instructions, address_lsbs, priv_mode_m;


   // HSV access fault crosses
   cp_hsv_access_fault: cross hsvb_hsvh_hsvw_instructions, illegal_address, priv_mode_m;


   // HTINST/XTINST crosses - transformed instruction encoding
   // Execute if Zca not supported?
   cp_xtinst_instr_misaligned_1: cross jal, pc_bit_1, imm_bit_1, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;

   cp_xtinst_instr_access: cross jalr, illegal_address, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;
   cp_xtinst_illegalinstr: cross illegalops, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;
   cp_xtinst_breakpoint: cross ebreak, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;
   cp_xtinst_virtinstr: cross csrr, vstval, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;

   // Execute if Zicclsm not supported?
   cp_xtinst_load_misaligned: cross loadop, addr_misaligned, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;

   cp_xtinst_load_access: cross loadop, illegal_address, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;

   // Execute if Zicclsm not supported?
   cp_xtinst_store_misaligned: cross storeop, addr_misaligned, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;

   cp_xtinst_store_access: cross storeop, illegal_address, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;
   cp_xtinst_ecall: cross ecall, priv_mode_vs, medeleg_except_ecall, hedeleg_disabled;


endgroup


function void exceptionsh_sample(int hart, int issue, ins_t ins);
   ExceptionsH_exceptions_cg.sample(ins);
endfunction
