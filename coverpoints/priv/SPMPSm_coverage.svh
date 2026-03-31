///////////////////////////////////////////
//
// RISC-V Architectural Functional Coverage Covergroups
// SPMP (S-level Physical Memory Protection) Test Suite
//
// Copyright (C) 2026 RISC-V International
//
// SPDX-License-Identifier: Apache-2.0
//
////////////////////////////////////////////////////////////////////////////////////////////////

`define COVER_SPMPSM

///////////////////////////////////////////
// CSR Access Covergroup
///////////////////////////////////////////
covergroup SPMPSm_csr_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    //------------------------------------------
    // cp_spmp_indirect_access: Test indirect CSR access via siselect/sireg/sireg2
    // Covers: writing siselect with SPMP range values (0x100-0x13F),
    //         then reading/writing sireg (spmpaddr) and sireg2 (spmpcfg)
    //------------------------------------------
    siselect_val: coverpoint ins.current.csr[`CSR_SISELECT] {
        bins spmp_entry[4] = {[12'h100:12'h13F]};
    }

    cp_spmp_indirect_access: coverpoint ins.current.insn {
        wildcard bins csrrw_sireg  = {CSRRW};
        wildcard bins csrrs_sireg  = {CSRRS};
        wildcard bins csrrc_sireg  = {CSRRC};
    }

    //------------------------------------------
    // cp_spmpaddr_write: Write and readback spmpaddr via sireg
    //------------------------------------------
    cp_spmpaddr_write: coverpoint ins.current.csr[`CSR_SIREG] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins addr_zero = {0};
        bins addr_nonzero = {[1:$]};
    }

    //------------------------------------------
    // cp_spmpcfg_write: Write and readback spmpcfg via sireg2
    // Tests that R, W, X, A, L, U, SHARED fields are writable
    //------------------------------------------
    cp_spmpcfg_write: coverpoint ins.current.csr[`CSR_SIREG2][9:0] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        // A field encodings (bits [4:3])
        bins a_off   = {10'b??_?_?_00_???} with (item[4:3] == 2'b00);
        bins a_tor   = {10'b??_?_?_01_???} with (item[4:3] == 2'b01);
        bins a_na4   = {10'b??_?_?_10_???} with (item[4:3] == 2'b10);
        bins a_napot = {10'b??_?_?_11_???} with (item[4:3] == 2'b11);
    }

    //------------------------------------------
    // cp_spmp_lock: Setting the L bit
    //------------------------------------------
    cp_spmp_lock: coverpoint ins.current.csr[`CSR_SIREG2][7] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins locked = {1};
        bins unlocked = {0};
    }

    //------------------------------------------
    // cp_spmp_lock_write_ignored: Writes to locked entry via siselect are ignored
    //------------------------------------------
    cp_spmp_lock_write_ignored: coverpoint {
        ins.prev.csr[`CSR_SIREG2][7],
        ins.current.insn[14:12]
    } iff (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
           ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins locked_csrrw = {4'b1_001};
        bins locked_csrrs = {4'b1_010};
        bins locked_csrrc = {4'b1_011};
    }

    //------------------------------------------
    // cp_spmp_lock_tor_prevaddr: Locked TOR entry also locks previous spmpaddr
    //------------------------------------------
    cp_spmp_lock_tor_prevaddr: coverpoint {
        ins.prev.csr[`CSR_SIREG2][7],
        ins.prev.csr[`CSR_SIREG2][4:3]
    } {
        bins locked_tor = {3'b1_01};
    }

    //------------------------------------------
    // cp_spmp_oob_access: Out-of-bound siselect index reads zero, writes ignored
    //------------------------------------------
    cp_spmp_oob_access: coverpoint ins.current.csr[`CSR_SISELECT] {
        bins oob_index = {[12'h140:12'h1FF]};
    }

    //------------------------------------------
    // cp_sfence_ordering: SFENCE.VMA after SPMP CSR writes
    //------------------------------------------
    cp_sfence_ordering: coverpoint ins.current.insn {
        wildcard bins sfence_vma = {SFENCE_VMA};
    }

    //------------------------------------------
    // cp_mpmpdeleg_pmpnum: mpmpdeleg.pmpnum field values
    //------------------------------------------
    cp_mpmpdeleg_pmpnum: coverpoint ins.current.csr[`CSR_MPMPDELEG][6:0] {
        bins zero_all_delegated = {0};
        bins partial[4] = {[1:62]};
        bins max_none_delegated = {[63:$]};
    }

    //------------------------------------------
    // cp_mpmpdeleg_locked: Cannot set pmpnum below locked PMP entry
    //------------------------------------------
    cp_mpmpdeleg_locked: coverpoint ins.current.csr[`CSR_MPMPDELEG][6:0] {
        bins pmpnum_val[4] = {[0:63]};
    }

    //------------------------------------------
    // cp_mmode_indirect_access: M-mode access to SPMP via miselect/mireg
    //------------------------------------------
    cp_mmode_indirect_access: coverpoint ins.current.csr[`CSR_MISELECT] iff
        (ins.prev.mode == 2'b11) {
        bins spmp_range[4] = {[12'h100:12'h13F]};
    }

    //------------------------------------------
    // cp_spmp_lock_clear_mmode: M-mode can clear L bit via miselect
    //------------------------------------------
    cp_spmp_lock_clear_mmode: coverpoint {
        ins.prev.csr[`CSR_MIREG2][7],
        ins.current.csr[`CSR_MIREG2][7]
    } iff (ins.prev.mode == 2'b11 &&
           ins.current.csr[`CSR_MISELECT] >= 12'h100 &&
           ins.current.csr[`CSR_MISELECT] <= 12'h13F) {
        bins clear_lock = {2'b10};  // was locked, now unlocked
    }

endgroup

///////////////////////////////////////////
// Permission Enforcement Covergroup
///////////////////////////////////////////
covergroup SPMPSm_perm_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    //------------------------------------------
    // Access type building block
    //------------------------------------------
    access_type: coverpoint ins.current.trap {
        type_option.weight = 0;
        bins no_trap = {0};
        bins trap    = {1};
    }

    //------------------------------------------
    // cp_smode_rule: S-mode-only rule (SHARED=0, U=0)
    // S-mode: Enforced with R/W/X permissions
    // U-mode: Denied
    //------------------------------------------
    smode_rule_rwx: coverpoint ins.current.csr[`CSR_SIREG2][2:0] iff
        (ins.current.csr[`CSR_SIREG2][9] == 0 &&
         ins.current.csr[`CSR_SIREG2][8] == 0) {
        type_option.weight = 0;
        bins r_only = {3'b100};
        bins rw     = {3'b110};
        bins rx     = {3'b101};
        bins rwx    = {3'b111};
        bins x_only = {3'b001};
    }

    cp_smode_rule: cross smode_rule_rwx, priv_mode_m_s, access_type;

    //------------------------------------------
    // cp_umode_rule: U-mode rule (SHARED=0, U=1)
    // U-mode: Enforced
    // S-mode (SUM=1): EnforceNoX
    // S-mode (SUM=0): Denied
    //------------------------------------------
    umode_rule_rwx: coverpoint ins.current.csr[`CSR_SIREG2][2:0] iff
        (ins.current.csr[`CSR_SIREG2][9] == 0 &&
         ins.current.csr[`CSR_SIREG2][8] == 1) {
        type_option.weight = 0;
        bins r_only = {3'b100};
        bins rw     = {3'b110};
        bins rx     = {3'b101};
        bins rwx    = {3'b111};
        bins x_only = {3'b001};
    }

    cp_umode_rule: cross umode_rule_rwx, priv_mode_u, access_type;

    //------------------------------------------
    // cp_sum_effect: SUM bit effect on S-mode access to U-mode regions
    //------------------------------------------
    sum_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "sum")[0] {
        type_option.weight = 0;
        bins sum_0 = {0};
        bins sum_1 = {1};
    }

    cp_sum_effect: cross umode_rule_rwx, sum_bit, priv_mode_s, access_type;

    //------------------------------------------
    // cp_mxr_effect: MXR bit effect (Make eXecutable Readable)
    //------------------------------------------
    mxr_bit: coverpoint get_csr_val(ins.hart, ins.issue, `SAMPLE_BEFORE, "sstatus", "mxr")[0] {
        type_option.weight = 0;
        bins mxr_0 = {0};
        bins mxr_1 = {1};
    }

    cp_mxr_effect: cross smode_rule_rwx, mxr_bit, access_type;

    //------------------------------------------
    // cp_shared_rule: Shared-Region rule (SHARED=1, U=1)
    // Both S and U mode: Enforced
    // RWX=000: Enforce/Enforce (no access)
    // RWX=100: Enforce/Read-only
    // RWX=110: Enforce/Enforce
    // RWX=001: Enforce/Enforce
    // RWX=101: Enforce/Exec-only
    // RWX=111: Enforce/Enforce
    //------------------------------------------
    shared_rule_rwx: coverpoint ins.current.csr[`CSR_SIREG2][2:0] iff
        (ins.current.csr[`CSR_SIREG2][9] == 1 &&
         ins.current.csr[`CSR_SIREG2][8] == 1) {
        type_option.weight = 0;
        bins none     = {3'b000};
        bins r_only   = {3'b100};
        bins rw       = {3'b110};
        bins x_only   = {3'b001};
        bins rx       = {3'b101};
        bins rwx      = {3'b111};
    }

    cp_shared_rule: cross shared_rule_rwx, priv_mode_m_s, access_type;

    //------------------------------------------
    // cp_reserved_encoding: RWX=010 and RWX=011 are reserved
    //------------------------------------------
    cp_reserved_encoding: coverpoint ins.current.csr[`CSR_SIREG2][2:0] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins rwx_010 = {3'b010};
        bins rwx_011 = {3'b011};
    }

    //------------------------------------------
    // cp_no_match_deny: No matching entry denies access
    //------------------------------------------
    cp_no_match_deny: coverpoint ins.current.trap iff
        (ins.prev.mode != 2'b11) {  // Not M-mode
        bins denied = {1};
    }

    //------------------------------------------
    // SPMP fault coverpoints (page fault exception codes)
    //------------------------------------------
    cp_spmp_fault_instr: coverpoint ins.current.csr[`CSR_SCAUSE] iff (ins.current.trap == 1) {
        bins instr_page_fault = {12};
    }

    cp_spmp_fault_load: coverpoint ins.current.csr[`CSR_SCAUSE] iff (ins.current.trap == 1) {
        bins load_page_fault = {13};
    }

    cp_spmp_fault_store: coverpoint ins.current.csr[`CSR_SCAUSE] iff (ins.current.trap == 1) {
        bins store_page_fault = {15};
    }

    //------------------------------------------
    // cp_mmode_bypass: M-mode memory access bypasses SPMP
    //------------------------------------------
    cp_mmode_bypass: coverpoint ins.current.trap iff
        (ins.prev.mode == 2'b11) {
        bins no_trap = {0};
    }

endgroup

///////////////////////////////////////////
// Address Matching Covergroup
///////////////////////////////////////////
covergroup SPMPSm_addr_cg with function sample(ins_t ins);
    option.per_instance = 0;

    `include "general/RISCV_coverage_standard_coverpoints.svh"

    //------------------------------------------
    // cp_addr_match_off: A=OFF, entry is disabled
    //------------------------------------------
    cp_addr_match_off: coverpoint ins.current.csr[`CSR_SIREG2][4:3] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins off = {2'b00};
    }

    //------------------------------------------
    // cp_addr_match_tor: A=TOR, top-of-range matching
    //------------------------------------------
    cp_addr_match_tor: coverpoint ins.current.csr[`CSR_SIREG2][4:3] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins tor = {2'b01};
    }

    //------------------------------------------
    // cp_addr_match_na4: A=NA4, naturally aligned 4-byte region
    //------------------------------------------
    cp_addr_match_na4: coverpoint ins.current.csr[`CSR_SIREG2][4:3] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins na4 = {2'b10};
    }

    //------------------------------------------
    // cp_addr_match_napot: A=NAPOT, naturally aligned power-of-two region
    //------------------------------------------
    cp_addr_match_napot: coverpoint ins.current.csr[`CSR_SIREG2][4:3] iff
        (ins.current.csr[`CSR_SISELECT] >= 12'h100 &&
         ins.current.csr[`CSR_SISELECT] <= 12'h13F) {
        bins napot = {2'b11};
    }

    //------------------------------------------
    // cp_priority_match: Lower-numbered entry has higher priority
    //------------------------------------------
    cp_priority_match: coverpoint ins.current.trap {
        bins match_trap = {1};
        bins match_allow = {0};
    }

    //------------------------------------------
    // cp_partial_match_fault: Access spans entry boundary -> fault
    //------------------------------------------
    cp_partial_match_fault: coverpoint ins.current.trap iff (ins.current.trap == 1) {
        bins partial_fault = {1};
    }

endgroup

///////////////////////////////////////////
// SPMP and Paging Covergroup
///////////////////////////////////////////
covergroup SPMPSm_paging_cg with function sample(ins_t ins);
    option.per_instance = 0;

    //------------------------------------------
    // cp_satp_bare_spmp: satp.mode == Bare with Sspmp active
    //------------------------------------------
    cp_satp_bare_spmp: coverpoint ins.current.csr[`CSR_SATP] {
        `ifdef XLEN64
            bins bare_mode = {0} with (item[63:60] == 4'b0000);
        `else
            bins bare_mode = {0} with (item[31] == 1'b0);
        `endif
    }

endgroup

///////////////////////////////////////////
// Sample function
///////////////////////////////////////////
function void spmpsm_sample(int hart, int issue, ins_t ins);
    SPMPSm_csr_cg.sample(ins);
    SPMPSm_perm_cg.sample(ins);
    SPMPSm_addr_cg.sample(ins);
    SPMPSm_paging_cg.sample(ins);
endfunction
